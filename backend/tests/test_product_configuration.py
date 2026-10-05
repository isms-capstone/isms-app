from test_registry_auth_ui import authenticated_app


def test_product_categories_sla_and_selection_ownership(authenticated_app):
    client = authenticated_app
    def login(name):
        response = client.post('/api/v1/auth/login', data={'username': name, 'password': 'test-only-password'})
        return {'Authorization': 'Bearer ' + response.json()['access_token']}
    admin, agent = login('qa-admin'), login('qa-agent')
    def post(path, body, status=201):
        result = client.post('/api/v1' + path, headers=admin, json=body)
        assert result.status_code == status, result.text
        return result.json()
    master = '/admin/master-data'
    products = [post('/products', {'name': name, 'code': name})['id'] for name in ['exam', 'logbook']]
    modules, symptoms, stages, problems, policies = [], [], [], [], []
    for product in products:
        modules.append(post(master + '/modules', {'name': 'Teacher', 'product_id': product})['id'])
        symptoms.append(post(master + '/symptoms', {'name': 'Login issue', 'product_id': product})['id'])
        stages.append(post(master + '/service-stages', {'name': 'During exam', 'product_id': product, 'sort_order': 2})['id'])
        problems.append(post(master + '/problem-types', {'name': 'Password', 'module_id': modules[-1]})['id'])
        policy = post(master + '/sla-policies', {'name': f'SLA {product}'})['id']
        policies.append(policy)
        post(master + f'/sla-policies/{policy}/rules', {'severity': 'S1', 'first_response_value': product,
             'first_response_unit': 'MINUTES', 'resolution_min_value': 1,
             'resolution_max_value': 2, 'resolution_unit': 'HOURS'})
        assigned = client.put(f'/api/v1/products/{product}/sla-policy', headers=admin, json={'sla_policy_id': policy})
        assert assigned.status_code == 200
        assert assigned.json()['sla_policy_id'] == policy
    for index, product in enumerate(products):
        context = client.get(f'/api/v1/products/{product}/case-options', headers=agent).json()
        assert [row['id'] for row in context['modules']] == [modules[index]]
        assert [row['id'] for row in context['symptoms']] == [symptoms[index]]
        assert [row['id'] for row in context['service_stages']] == [stages[index]]
        assert [row['id'] for row in context['problem_types']] == [problems[index]]
        assert context['sla_policy']['id'] == policies[index]
        selection = {'module_id': modules[index], 'symptom_id': symptoms[index],
                     'service_stage_id': stages[index], 'problem_type_id': problems[index]}
        result = client.post(f'/api/v1/products/{product}/validate-case-options', headers=agent, json=selection)
        assert result.status_code == 200 and result.json() == selection
        for key in selection:
            foreign = dict(selection, **{key: {'module_id': modules[1-index], 'symptom_id': symptoms[1-index],
                           'service_stage_id': stages[1-index], 'problem_type_id': problems[1-index]}[key]})
            assert client.post(f'/api/v1/products/{product}/validate-case-options', headers=agent, json=foreign).status_code == 422
    # Admin edits are immediately visible without restart; inactive options disappear.
    symptom_path = f'/api/v1{master}/symptoms/{symptoms[0]}'
    assert client.patch(symptom_path, headers=admin, json={'name': 'Renamed symptom'}).status_code == 200
    assert client.get(f'/api/v1/products/{products[0]}/case-options', headers=agent).json()['symptoms'][0]['name'] == 'Renamed symptom'
    assert client.delete(symptom_path, headers=admin).status_code == 200
    assert client.get(f'/api/v1/products/{products[0]}/case-options', headers=agent).json()['symptoms'] == []
    assert client.put(f'/api/v1/products/{products[0]}/sla-policy', headers=agent, json={'sla_policy_id': policies[1]}).status_code == 403
    assert client.put(f'/api/v1/products/{products[0]}/sla-policy', headers=admin, json={'sla_policy_id': 999}).status_code == 404
    assert client.delete(f'/api/v1{master}/sla-policies/{policies[0]}', headers=admin).status_code == 200
    context = client.get(f'/api/v1/products/{products[0]}/case-options', headers=agent).json()
    assert context['configured_sla_policy_id'] == policies[0] and context['sla_policy'] is None
    assert client.put(f'/api/v1/products/{products[0]}/sla-policy', headers=admin, json={'sla_policy_id': policies[0]}).status_code == 409
    assert client.put(f'/api/v1/products/{products[0]}/sla-policy', headers=admin, json={'sla_policy_id': None}).status_code == 200
    assert client.get(f'/api/v1/products/{products[0]}/case-options').status_code == 401
    post(master + '/modules', {'name': 'x' * 101, 'product_id': products[0]}, 422)
    post(master + '/problem-types', {'name': 'x' * 101, 'module_id': modules[0]}, 422)
    assert client.patch(f'/api/v1{master}/problem-types/{problems[0]}', headers=admin,
                        json={'name': ' '}).status_code == 422
    rules = client.get(f'/api/v1{master}/sla-policies/{policies[1]}/rules', headers=admin).json()
    assert client.patch(f'/api/v1{master}/sla-policies/{policies[1]}/rules/{rules[0]["id"]}',
                        headers=admin, json={'resolution_min_value': None}).status_code == 422
