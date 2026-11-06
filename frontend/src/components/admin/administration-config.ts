import { channelNames, statusNames } from "@/lib/types";
import type { Collection, Field } from "./master-data-config";

const master = "/admin/master-data";
const name: Field = { key: "name", label: "ชื่อ", max: 150 };
const description: Field = {
  key: "description",
  label: "รายละเอียด",
  type: "textarea",
  optional: true,
  max: 255,
};
const severity = ["S1", "S2", "S3", "S4"];
const units = ["MINUTES", "HOURS", "BUSINESS_DAYS"];
const weekdays = Object.entries({
  monday: "วันจันทร์",
  tuesday: "วันอังคาร",
  wednesday: "วันพุธ",
  thursday: "วันพฤหัสบดี",
  friday: "วันศุกร์",
  saturday: "วันเสาร์",
  sunday: "วันอาทิตย์",
});
const conditions = {
  product_id: { source: `${master}/products` },
  module_id: { source: `${master}/modules` },
  problem_type_id: { source: `${master}/problem-types` },
  ticket_type_id: { source: `${master}/ticket-types` },
  symptom_id: { source: `${master}/symptoms` },
  service_stage_id: { source: `${master}/service-stages` },
  severity: { choices: severity },
  status: { choices: Object.keys(statusNames) },
  channel: {
    choices: [
      ...new Set([
        ...Object.keys(channelNames),
        ...Object.values(channelNames),
      ]),
    ],
  },
};

export const administrationGroups = [
  {
    title: "Users & Teams",
    description: "จัดการบัญชีผู้ใช้ ทีม และบทบาท",
    sections: ["users", "teams", "roles"],
  },
  {
    title: "SLA & Business Hours",
    description: "กำหนดเวลาให้บริการ เป้าหมายตามความรุนแรง และวันหยุด",
    sections: ["sla-policies", "business-calendars"],
  },
  {
    title: "Automation Rules",
    description: "กำหนดเงื่อนไขมอบหมายเคสให้ทีมโดยอัตโนมัติ",
    sections: ["automation"],
  },
];

export const administrationCollections: Record<string, Collection> = {
  users: {
    title: "ผู้ใช้",
    titleKey: "username",
    path: "/admin/users",
    removable: true,
    fields: [
      { key: "username", label: "ชื่อผู้ใช้", createOnly: true },
      { key: "email", label: "อีเมล", type: "email" },
      { key: "full_name", label: "ชื่อเต็ม", optional: true },
      {
        key: "password",
        label: "รหัสผ่าน",
        type: "password",
        optionalOnEdit: true,
      },
      { key: "role_id", label: "บทบาท", source: "/roles" },
      { key: "team_id", label: "ทีม", source: "/teams", optional: true },
    ],
  },
  teams: {
    title: "ทีม",
    path: "/teams",
    fields: [name, description],
    noStatus: true,
    removable: true,
  },
  roles: {
    title: "บทบาท",
    path: "/roles",
    fields: [name, description],
    noStatus: true,
    removable: true,
    lockedNames: [
      "Admin",
      "Agent",
      "Specialist",
      "Developer",
      "Team Lead",
      "Executive",
    ],
  },
  "sla-policies": {
    title: "นโยบาย SLA",
    path: `${master}/sla-policies`,
    fields: [name, description],
    child: {
      title: "กฎ SLA",
      titleKey: "severity",
      suffix: "rules",
      fields: [
        { key: "severity", label: "ความรุนแรง", choices: severity },
        {
          key: "first_response_value",
          label: "เวลาตอบกลับครั้งแรก",
          type: "number",
        },
        {
          key: "first_response_unit",
          label: "หน่วยเวลาตอบกลับ",
          choices: units,
        },
        {
          key: "resolution_min_value",
          label: "เวลาแก้ไขขั้นต่ำ",
          type: "number",
        },
        {
          key: "resolution_max_value",
          label: "เวลาแก้ไขสูงสุด",
          type: "number",
        },
        { key: "resolution_unit", label: "หน่วยเวลาแก้ไข", choices: units },
        {
          key: "business_hours_only",
          label: "นับเฉพาะเวลาทำการ",
          type: "boolean",
          defaultValue: "true",
        },
      ],
    },
  },
  "business-calendars": {
    title: "ปฏิทินเวลาทำการ",
    path: `${master}/business-calendars`,
    fields: [
      name,
      {
        key: "timezone",
        label: "เขตเวลา",
        defaultValue: "Asia/Bangkok",
        max: 64,
      },
      {
        key: "work_start_time",
        label: "เริ่มงาน",
        type: "time",
        defaultValue: "08:00",
      },
      {
        key: "work_end_time",
        label: "เลิกงาน",
        type: "time",
        defaultValue: "17:00",
      },
      ...weekdays.map(([key, label], index): Field => ({
        key,
        label,
        type: "boolean",
        defaultValue: String(index < 5),
      })),
      description,
    ],
    child: {
      title: "วันหยุด",
      suffix: "holidays",
      fields: [
        name,
        { key: "holiday_date", label: "วันที่", type: "date" },
        {
          key: "holiday_type",
          label: "ประเภทวันหยุด",
          choices: ["ANNUAL", "SPECIAL"],
          defaultValue: "ANNUAL",
        },
        description,
      ],
    },
  },
  automation: {
    title: "กฎอัตโนมัติ",
    path: "/admin/automation-rules",
    fields: [
      name,
      {
        key: "priority",
        label: "ลำดับความสำคัญ",
        type: "number",
        defaultValue: "100",
      },
      {
        key: "condition_field",
        label: "เงื่อนไข",
        choices: Object.keys(conditions),
      },
      {
        key: "condition_value",
        label: "ค่าที่ต้องตรงกัน",
        dependsOn: "condition_field",
        sourceBy: conditions,
      },
      { key: "action_team_id", label: "ทีมที่รับเคส", source: "/teams" },
      description,
    ],
  },
};
