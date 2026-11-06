type Field = {
  key: string;
  label: string;
  type?: "number" | "url" | "textarea";
  max?: number;
  optional?: boolean;
  defaultValue?: string;
  source?: string;
  choices?: string[];
  dependsOn?: string;
  createOnly?: boolean;
};

type Collection = {
  title: string;
  path: string;
  fields: Field[];
  registry?: boolean;
};

const master = "/admin/master-data";
const name: Field = { key: "name", label: "ชื่อ", max: 150 };
const shortName = { ...name, max: 100 };
const description: Field = {
  key: "description",
  label: "รายละเอียด",
  type: "textarea",
  max: 255,
  optional: true,
};
const code: Field = { key: "code", label: "รหัส", max: 50 };
const product: Field = {
  key: "product_id",
  label: "ผลิตภัณฑ์",
  source: `${master}/products`,
};
const moduleField: Field = {
  key: "module_id",
  label: "โมดูล",
  source: `${master}/modules`,
};
const collections = [
  ["products", "ผลิตภัณฑ์", [name, description]],
  ["modules", "โมดูล", [product, shortName, description]],
  ["problem-types", "ประเภทปัญหา", [moduleField, shortName, description]],
  ["symptoms", "อาการ", [product, name, description]],
  [
    "service-stages",
    "ขั้นตอนบริการ",
    [
      product,
      shortName,
      { key: "sort_order", label: "ลำดับ", type: "number", defaultValue: "1" },
      description,
    ],
  ],
  ["ticket-types", "ประเภทเคส", [name, description]],
  ["cause-codes", "สาเหตุปัญหา", [code, name, description]],
  ["solution-codes", "วิธีแก้ไข", [code, name, description]],
  [
    "case-templates",
    "เทมเพลตเคส",
    [
      name,
      product,
      { ...moduleField, dependsOn: "product_id" },
      {
        key: "problem_type_id",
        label: "ประเภทปัญหา",
        source: `${master}/problem-types`,
        dependsOn: "module_id",
      },
      {
        key: "default_severity",
        label: "ความรุนแรง",
        choices: ["S1", "S2", "S3", "S4"],
      },
      description,
    ],
  ],
  [
    "canned-messages",
    "ข้อความสำเร็จรูป",
    [
      name,
      { key: "message", label: "ข้อความ", type: "textarea", max: 5000 },
      description,
    ],
  ],
] satisfies [string, string, Field[]][];

export const masterCollections: Record<string, Collection> = {
  ...Object.fromEntries(
    collections.map(([key, title, fields]) => [
      key,
      { title, path: `${master}/${key}`, fields },
    ]),
  ),
  organizations: {
    title: "องค์กรลูกค้า",
    path: "/customers/organizations",
    fields: [{ ...name, max: 255 }],
    registry: true,
  },
  "customer-systems": {
    title: "ระบบที่ลูกค้าใช้งาน",
    path: "/product-instances",
    registry: true,
    fields: [
      {
        key: "organization_id",
        label: "องค์กรลูกค้า",
        source: "/customers/organizations",
        createOnly: true,
      },
      { ...product, source: "/products", createOnly: true },
      code,
      { ...name, max: 255 },
      { key: "version", label: "เวอร์ชัน", max: 100 },
      { key: "environment", label: "Environment", max: 50 },
      { key: "url", label: "URL", type: "url", max: 2048 },
    ],
  },
};
