# Product integration — POR-01 to POR-06

Add a Report a problem button to the product. On click, the product server checks its existing session and resolves the customer's ISMS IDs from its trusted mapping. It issues the grant below and returns a form that POSTs the token to `https://isms.example/portal/sso-entry`. Open this as a top-level page or product popup. Use the same button to obtain a fresh grant when checking replies.

## HS256 contract

Set `POR_PRODUCTS` on the ISMS API as an environment secret. Example shape:

```json
{"ExamPlus":{"secret":"<unique random secret of at least 32 bytes>","product_id":1,"intake_user_id":7,"origins":["https://exam.example"]}}
```

Use a dedicated active intake account. Only the product server and ISMS hold its HMAC secret. Each product gets a different random secret. The signed email must be verified by the product. IDs refer to active customer, product instance and module records in ISMS.

```text
now = unix_seconds()
claims = {
  iss: "ExamPlus", aud: "isms-portal", sub: product_user.id_as_string,
  jti: random_uuid(), iat: now, exp: now + 300,
  organization_id: 42, instance_id: 8, module_id: 3,
  name: product_user.display_name, email: product_user.verified_email,
  source_url: "https://exam.example/attempt/123",
  exam_or_course_context: "EXAM-123"
}
token = jwt_sign(claims, product_secret, algorithm="HS256")
return HTML form(method="POST", action=isms_origin + "/portal/sso-entry",
                 hidden_fields={token: token})
```

The form must HTML-escape the token and use HTTPS in production. Keep grants out of URLs, logs and browser storage. Keep the encoded grant at or below 3,800 characters so it fits the browser cookie. Each grant creates one case. Retrying it returns the existing case number. They can view their latest 50 cases for the same product instance and see public Portal replies while the grant is valid. An expired grant requires clicking the product button again. The case stores the screen URL without query or fragment, the browser user agent and the optional course or exam code. The user can upload or paste PNG, JPEG or WebP up to 10 MB.

## Agent replies and email

Open the same case detail used for other channels and post an external reply with channel Portal. Internal worklogs stay staff-only. The portal refreshes every 15 seconds and the worker sends an email without the reply body. Configure `POR_SMTP_HOST`, `POR_SMTP_FROM`, optional `POR_SMTP_PORT` (587), and `POR_SMTP_USER` / `POR_SMTP_PASSWORD` for authenticated STARTTLS. Pass these variables to the routing worker process and keep it running. Unsent records stay queued. SMTP delivery can repeat if delivery succeeds before a database commit fails.

Apply the Alembic migration before starting the API or worker. Product deployment requires a team to configure its button, mapping and shared secret.
