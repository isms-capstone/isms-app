import {mountCustomerAutocomplete} from './autocomplete.js';

const workspace = document.querySelector('#workspace');
const dialog = document.querySelector('#editor');
let token = '', user = null, currentView = 'work', disposePicker = null, saveAction = null, renderVersion = 0;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}
function notify(message, error = false) {
  const node = document.querySelector('#notice');
  node.textContent = message; node.className = error ? 'error' : ''; node.hidden = false;
}
function failure(error) { if (error.name !== 'AbortError') notify(error.message, true); }
function button(label, action, className) {
  const node = element('button', label, className); node.type = 'button';
  node.addEventListener('click', () => Promise.resolve().then(action).catch(failure));
  return node;
}
async function request(path, options = {}) {
  const headers = {...options.headers};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body = options.body;
  if (body && !(body instanceof URLSearchParams)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
  const response = await fetch(`/api/v1${path}`, {...options, headers, body});
  const result = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401 && token) signOut();
    const detail = Array.isArray(result?.detail) ? result.detail.map(x => `${x.loc.at(-1)}: ${x.msg}`).join('; ') : result?.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return result;
}
async function all(path) {
  const records = [];
  for (let offset = 0; ; offset += 100) {
    const page = await request(`${path}${path.includes('?') ? '&' : '?'}offset=${offset}&limit=100`);
    records.push(...page);
    if (page.length < 100) return records;
  }
}
function badge(active) { return element('span', active ? 'ใช้งาน' : 'ปิดใช้งาน', `badge${active ? '' : ' inactive'}`); }
function startView(title, description) {
  ++renderVersion;
  disposePicker?.(); disposePicker = null;
  workspace.replaceChildren();
  document.body.classList.remove('mobile-menu-open');
  const heading = element('div', null, 'heading'), copy = element('div');
  copy.append(element('h1', title), element('p', description)); heading.append(copy); workspace.append(heading);
  return heading;
}
function section(title, actionLabel, action, allowed) {
  const card = element('section', null, 'card'), heading = element('div', null, 'section-title');
  heading.append(element('h2', title));
  if (allowed) heading.append(button(actionLabel, action, 'primary'));
  card.append(heading); workspace.append(card); return card;
}
function table(card, columns, rows, actions) {
  const wrap = element('div', null, 'table-wrap'), grid = element('table');
  const head = element('tr'); columns.forEach(c => head.append(element('th', c[0])));
  if (actions) head.append(element('th', 'จัดการ'));
  const thead = element('thead'); thead.append(head); grid.append(thead);
  const tbody = element('tbody');
  for (const row of rows) {
    const tr = element('tr');
    columns.forEach(([, value]) => { const td = element('td'), result = value(row); td.dataset.label = columns.find(column => column[1] === value)[0]; td.append(result instanceof Node ? result : document.createTextNode(String(result ?? '—'))); tr.append(td); });
    if (actions) { const td = element('td', null, 'actions'); actions(row).forEach(b => td.append(b)); tr.append(td); }
    tbody.append(tr);
  }
  grid.append(tbody); wrap.append(grid); card.append(wrap);
  if (!rows.length) card.append(element('p', 'ยังไม่มีข้อมูล', 'empty'));
}
function collection(card, path, columns, actions, searchable = false) {
  let offset = 0, query = '', generation = 0;
  const toolbar = element('div', null, 'toolbar'), results = element('div');
  if (searchable) {
    const search = element('input'); search.placeholder = 'ค้นหาชื่อหรือรหัส'; search.setAttribute('aria-label', 'ค้นหาทะเบียน');
    const form = element('form', null, 'toolbar');
    const submit = element('button', 'ค้นหา'); submit.type = 'submit';
    form.append(search, submit); form.addEventListener('submit', e => { e.preventDefault(); query = search.value; offset = 0; load().catch(failure); }); toolbar.append(form);
  }
  card.append(toolbar, results);
  async function load() {
    const current = ++generation;
    const params = new URLSearchParams({offset, limit: 26}); if (searchable) params.set('q', query);
    const rows = await request(`${path}${path.includes('?') ? '&' : '?'}${params}`);
    if (current !== generation || !card.isConnected) return;
    results.replaceChildren(); table(results, columns, rows.slice(0, 25), actions);
    const pager = element('div', null, 'pager');
    const prev = button('ก่อนหน้า', async () => { offset -= 25; await load(); }); prev.disabled = offset === 0;
    const next = button('ถัดไป', async () => { offset += 25; await load(); }); next.disabled = rows.length <= 25;
    pager.append(prev, element('span', rows.length ? `${offset + 1}–${offset + Math.min(rows.length, 25)}` : '0 รายการ'), next); results.append(pager);
  }
  load().catch(failure); return load;
}

function field(name, label, type = 'text', options = {}) { return {name, label, type, ...options}; }
function edit(title, fields, record, save, reload) {
  document.querySelector('#editor-title').textContent = title;
  document.querySelector('#editor-error').textContent = '';
  const root = document.querySelector('#editor-fields'); root.replaceChildren();
  for (const spec of fields) {
    const label = element('label', spec.label), input = element(spec.type === 'select' ? 'select' : 'input');
    input.name = spec.name;
    input.setAttribute('aria-label', spec.label);
    if (spec.type === 'select') for (const option of spec.options) { const item = element('option', option.label); item.value = option.value ?? ''; input.append(item); }
    else { input.type = spec.type; if (spec.maxLength) input.maxLength = spec.maxLength; }
    input.required = spec.required !== false;
    const fallback = spec.type === 'select' ? input.options[0]?.value ?? '' : '';
    input.value = record?.[spec.name] ?? spec.default ?? fallback;
    label.append(input); root.append(label);
  }
  saveAction = async () => {
    const form = document.querySelector('#editor-form'), values = {};
    for (const spec of fields) {
      let value = form.elements.namedItem(spec.name).value;
      if (spec.boolean) value = value === 'true';
      if (spec.number) value = value ? Number(value) : null;
      if (spec.type === 'date' && !value) value = null;
      if (spec.type === 'datetime-local') value = new Date(value).toISOString();
      values[spec.name] = value;
    }
    await save(values); dialog.close(); notify('บันทึกข้อมูลแล้ว'); await reload();
  };
  dialog.showModal();
}
const activeField = field('is_active', 'สถานะ', 'select', {boolean: true, default: true, options: [{value: true, label: 'ใช้งาน'}, {value: false, label: 'ปิดใช้งาน'}]});
const nameFields = [field('name', 'ชื่อ', 'text', {maxLength: 255}), activeField];
const codeFields = [field('code', 'รหัส (a-z, 0-9, ขีดกลาง/ขีดล่าง)', 'text', {maxLength: 50}), ...nameFields];
const productFields = codeFields.map(spec => spec.name === 'name' ? {...spec, maxLength: 150} : spec);
const moduleFields = codeFields.map(spec => spec.name === 'name' ? {...spec, maxLength: 100} : spec);
const orgPath = id => `/customers/organizations/${id}`;
const save = async (path, method, body) => { const result = await request(path, {method, body}); if (path === '/products' || /^\/products\/\d+$/.test(path)) await refreshProductNavigation(); return result; };

async function showCustomers() {
  startView('ลูกค้า', 'ทะเบียนองค์กร ผู้ติดต่อ และช่องทางติดต่อ');
  let reload;
  const card = section('องค์กรลูกค้า', '+ เพิ่มองค์กร', () => edit('เพิ่มองค์กร', nameFields, {}, body => save('/customers/organizations', 'POST', body), reload), user.can_edit_customers);
  reload = collection(card, '/customers/organizations', [['องค์กร', row => button(row.name, () => showOrganization(row), 'link')], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_customers ? [button('แก้ไข', () => edit('แก้ไของค์กร', nameFields, row, body => save(orgPath(row.id), 'PUT', body), reload))] : [], true);
}
function localDateTime(value) {
  const date = new Date(value); return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
async function showOrganization(org) {
  startView(org.name, 'ผู้ติดต่อ ระบบที่ใช้งาน หน่วยงาน รายวิชา และปฏิทินสำคัญ');
  const version = renderVersion;
  workspace.prepend(button('← กลับทะเบียนลูกค้า', showCustomers));
  const contract = await request(`${orgPath(org.id)}/contract`);
  if (version !== renderVersion || !user) return;
  const overview = await request(`${orgPath(org.id)}/case-summary`);
  if (version !== renderVersion || !user) return;
  const openCases = section(`เคสที่เปิดอยู่ (${overview.open_count})`, '', null, false);
  collection(openCases, `/tickets?organization_id=${org.id}&open_only=true`, [
    ['เลขเคส', row => button(row.ticket_no, () => showTicket(row.id), 'link')],
    ['หัวข้อ', row => row.subject], ['สถานะ', row => row.status],
    ['เวลาที่แจ้ง', row => new Date(row.reported_at).toLocaleString('th-TH')]
  ]);
  const problems = section('ประวัติปัญหาที่พบบ่อย', '', null, false);
  problems.append(element('p', 'รวมเคสใหม่และเคสที่แก้ไขแล้ว แยกตามผลิตภัณฑ์/โมดูล/ประเภทปัญหา/อาการ ไม่รวมร่าง เคสซ้ำ และเคสยกเลิก', 'muted'));
  collection(problems, `${orgPath(org.id)}/problem-history`, [
    ['ผลิตภัณฑ์', row => row.product_name || 'ยังไม่ระบุ'], ['โมดูล', row => row.module_name || '—'],
    ['ประเภทปัญหา', row => row.category_name || 'ยังไม่จัดหมวดหมู่'], ['อาการ', row => row.symptom_name || '—'],
    ['จำนวนครั้ง', row => row.frequency], ['แจ้งล่าสุด', row => new Date(row.last_reported_at).toLocaleString('th-TH')]
  ]);
  const contractCard = section('สัญญาลูกค้า', 'แก้ไขสัญญา', () => edit('ช่วงสัญญา', [field('contract_start_date', 'วันเริ่มสัญญา', 'date', {required: false}), field('contract_end_date', 'วันสิ้นสุดสัญญา', 'date', {required: false})], contract, body => save(`${orgPath(org.id)}/contract`, 'PATCH', body), () => showOrganization(org)), user.can_edit_customers);
  contractCard.append(element('p', `${contract.contract_start_date || 'ยังไม่ระบุ'} → ${contract.contract_end_date || 'ยังไม่ระบุ'}`, 'muted'));
  let reloadContacts;
  const contacts = section('ผู้ติดต่อ', '+ เพิ่มผู้ติดต่อ', () => edit('เพิ่มผู้ติดต่อ', nameFields, {}, body => save(`${orgPath(org.id)}/contacts`, 'POST', body), reloadContacts), user.can_edit_customers);
  reloadContacts = collection(contacts, `/customers/contacts?organization_id=${org.id}`, [['ชื่อ', row => row.name], ['ช่องทาง', row => row.channels.map(c => `${c.channel_type}: ${c.value}`).join(' · ') || '—'], ['สถานะ', row => badge(row.is_active)]], row => [button('ช่องทางติดต่อ', () => showContact(org, row)), ...(user.can_edit_customers ? [button('แก้ไข', () => edit('แก้ไขผู้ติดต่อ', nameFields, row, body => save(`/customers/contacts/${row.id}`, 'PUT', body), reloadContacts))] : [])], true);
  let reloadInstances;
  async function instanceEditor(record = null) {
    const products = await all('/products?is_active=true');
    if (version !== renderVersion || !user) return;
    const fields = [...codeFields.slice(0, 2), field('version', 'เวอร์ชัน', 'text', {maxLength: 100}), field('environment', 'Environment', 'text', {maxLength: 50}), field('url', 'URL', 'url', {maxLength: 2048}), activeField];
    if (!record) fields.unshift(field('product_id', 'ผลิตภัณฑ์', 'select', {number: true, options: [{value: '', label: 'เลือกผลิตภัณฑ์'}, ...products.map(p => ({value: p.id, label: p.name}))]}));
    edit(record ? 'แก้ไขระบบที่ใช้งาน' : 'เพิ่มระบบที่ใช้งาน', fields, record || {}, body => {
      if (record) return save(`/product-instances/${record.id}`, 'PUT', body);
      const product = body.product_id; delete body.product_id;
      return save(`/organizations/${org.id}/products/${product}/instances`, 'POST', body);
    }, reloadInstances);
  }
  const instances = section('ระบบที่ลูกค้าใช้งาน', '+ เพิ่ม instance', () => instanceEditor(), user.can_edit_customers);
  const catalogue = await all('/products'); const productNames = new Map(catalogue.map(p => [p.id, p.name]));
  if (version !== renderVersion || !user) return;
  reloadInstances = collection(instances, `/product-instances?organization_id=${org.id}`, [['ระบบ', row => `${productNames.get(row.product_id) || row.product_id} · ${row.name}`], ['เวอร์ชัน / Environment', row => `${row.version} / ${row.environment}`], ['URL', row => row.url], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_customers ? [button('แก้ไข', () => instanceEditor(row))] : [], true);
  let reloadDepartments;
  const departments = section('หน่วยงาน', '+ เพิ่มหน่วยงาน', () => edit('เพิ่มหน่วยงาน', nameFields, {}, body => save(`${orgPath(org.id)}/departments`, 'POST', body), reloadDepartments), user.can_edit_customers);
  reloadDepartments = collection(departments, `${orgPath(org.id)}/departments`, [['หน่วยงาน', row => row.name], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_customers ? [button('แก้ไข', () => edit('แก้ไขหน่วยงาน', nameFields, row, body => save(`${orgPath(org.id)}/departments/${row.id}`, 'PUT', body), reloadDepartments))] : [], true);
  let reloadCourses;
  const courseFields = [field('kind', 'ประเภท', 'select', {default: 'course', options: [{value: 'course', label: 'รายวิชา'}, {value: 'exam', label: 'การสอบ'}]}), ...nameFields];
  const courses = section('รายวิชา / การสอบ', '+ เพิ่มรายการ', () => edit('เพิ่มรายวิชา / การสอบ', courseFields, {}, body => save(`${orgPath(org.id)}/courses`, 'POST', body), reloadCourses), user.can_edit_customers);
  reloadCourses = collection(courses, `${orgPath(org.id)}/courses`, [['ชื่อ', row => row.name], ['ประเภท', row => row.kind === 'course' ? 'รายวิชา' : 'การสอบ'], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_customers ? [button('แก้ไข', () => edit('แก้ไขรายวิชา / การสอบ', courseFields, row, body => save(`${orgPath(org.id)}/courses/${row.id}`, 'PUT', body), reloadCourses))] : [], true);
  let reloadWindows;
  async function windowEditor(record = null) {
    const departments = await all(`${orgPath(org.id)}/departments`);
    if (version !== renderVersion || !user) return;
    const fields = [field('name', 'ชื่อช่วงสอบ', 'text', {maxLength: 255}), field('department_id', 'หน่วยงาน', 'select', {number: true, required: false, options: [{value: '', label: 'ทั้งองค์กร'}, ...departments.map(d => ({value: d.id, label: d.name}))]}), field('starts_at', 'เริ่ม (เวลาท้องถิ่นของอุปกรณ์)', 'datetime-local'), field('ends_at', 'สิ้นสุด (เวลาท้องถิ่นของอุปกรณ์)', 'datetime-local'), activeField];
    edit(record ? 'แก้ไขช่วงสอบ' : 'เพิ่มช่วงสอบ', fields, record ? {...record, starts_at: localDateTime(record.starts_at), ends_at: localDateTime(record.ends_at)} : {}, body => save(`${orgPath(org.id)}/exam-windows${record ? `/${record.id}` : ''}`, record ? 'PUT' : 'POST', body), reloadWindows);
  }
  const windows = section('ปฏิทินช่วงสอบ', '+ เพิ่มช่วงสอบ', () => windowEditor(), user.can_edit_customers);
  reloadWindows = collection(windows, `${orgPath(org.id)}/exam-windows`, [['ช่วงสอบ', row => row.name], ['เริ่ม', row => new Date(row.starts_at).toLocaleString('th-TH')], ['สิ้นสุด', row => new Date(row.ends_at).toLocaleString('th-TH')], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_customers ? [button('แก้ไข', () => windowEditor(row))] : []);
}
async function showContact(org, contact) {
  startView(contact.name, org.name); workspace.prepend(button('← กลับข้อมูลลูกค้า', () => showOrganization(org)));
  const version = renderVersion;
  const current = await request(`/customers/contacts/${contact.id}`);
  if (version !== renderVersion || !user) return;
  const channels = section('ช่องทางติดต่อ', '+ เพิ่มช่องทาง', () => edit('เพิ่มช่องทางติดต่อ', [field('channel_type', 'ประเภทช่องทาง', 'select', {options: [{value: 'line_user_id', label: 'LINE userId'}, {value: 'line_group_id', label: 'LINE groupId'}, {value: 'email', label: 'อีเมล'}, {value: 'phone', label: 'โทรศัพท์'}]}), field('value', 'ข้อมูลช่องทาง', 'text', {maxLength: 255})], {}, body => save(`/customers/contacts/${contact.id}/channels`, 'POST', body), () => showContact(org, contact)), user.can_edit_customers);
  table(channels, [['ประเภท', row => row.channel_type], ['ข้อมูล', row => row.value]], current.channels, row => user.can_edit_customers ? [button('ลบช่องทาง', async () => {
    if (!confirm(`ลบช่องทาง ${row.value}?`)) return;
    await request(`/customers/contacts/${contact.id}/channels/${row.id}`, {method: 'DELETE'}); await showContact(org, contact);
  })] : []);
}
async function showProducts() {
  startView('ทะเบียนผลิตภัณฑ์', 'ระบบและโมดูลที่ทีมให้บริการ เพิ่มผลิตภัณฑ์ได้ตามการใช้งาน');
  let reload;
  const card = section('ผลิตภัณฑ์', '+ เพิ่มผลิตภัณฑ์', () => edit('เพิ่มผลิตภัณฑ์', productFields, {}, body => save('/products', 'POST', body), reload), user.can_edit_products);
  reload = collection(card, '/products', [['ผลิตภัณฑ์', row => button(row.name, () => showProduct(row), 'link')], ['รหัส', row => row.code], ['จำนวนโมดูล', row => row.modules.length], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_products ? [button('แก้ไข', () => edit('แก้ไขผลิตภัณฑ์', productFields, row, body => save(`/products/${row.id}`, 'PUT', body), reload))] : [], true);
}
async function showProduct(product) {
  startView(product.name, `รหัส ${product.code}`); workspace.prepend(button('← กลับทะเบียนผลิตภัณฑ์', showProducts));
  const version = renderVersion;
  const current = await request(`/products/${product.id}`), teams = await request('/registry/teams');
  if (version !== renderVersion || !user) return;
  const team = section('ทีมผู้รับผิดชอบเริ่มต้น', 'เลือกทีม', () => edit('ทีมผู้รับผิดชอบเริ่มต้น', [field('default_team_id', 'ทีม', 'select', {number: true, required: false, options: [{value: '', label: 'ยังไม่กำหนด'}, ...teams.map(t => ({value: t.id, label: t.name}))]})], current, body => save(`/products/${product.id}/default-team`, 'PUT', body), () => showProduct(product)), user.can_edit_products);
  team.append(element('p', teams.find(t => t.id === current.default_team_id)?.name || 'ยังไม่กำหนด', 'muted'));
  const reload = () => showProduct(product);
  const card = section('โมดูลของผลิตภัณฑ์', '+ เพิ่มโมดูล', () => edit('เพิ่มโมดูล', moduleFields, {}, body => save(`/products/${product.id}/modules`, 'POST', body), reload), user.can_edit_products);
  collection(card, `/products/${product.id}/modules`, [['ชื่อ', row => row.name], ['รหัส', row => row.code], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_products ? [button('แก้ไข', () => edit('แก้ไขโมดูล', moduleFields, row, body => save(`/products/${product.id}/modules/${row.id}`, 'PUT', body), reload))] : []);
  await showProductConfiguration(product, current, version);
}
async function showProductConfiguration(product, current, version) {
  const [options, policies] = await Promise.all([
    current.is_active ? request(`/products/${product.id}/case-options`) : Promise.resolve(null),
    user.can_edit_products ? request('/registry/sla-policies') : Promise.resolve([])
  ]);
  if (version !== renderVersion || !user) return;
  const reload = () => showProduct(product);
  const policyCard = section('นโยบาย SLA ของผลิตภัณฑ์', 'เลือกนโยบาย SLA', () => edit('เลือกนโยบาย SLA', [
    field('sla_policy_id', 'นโยบาย SLA', 'select', {number: true, required: false, options: [
      {value: '', label: 'ยังไม่กำหนด'}, ...policies.map(p => ({value: p.id, label: p.name}))
    ]})
  ], current, body => save(`/products/${product.id}/sla-policy`, 'PUT', body), reload), user.can_edit_products);
  const policy = options?.sla_policy;
  policyCard.append(element('p', policy?.name || (current.sla_policy_id ? 'นโยบายที่กำหนดถูกปิดใช้งาน' : 'ยังไม่กำหนดนโยบาย SLA'), 'muted'));
  if (user.can_edit_products) {
    policyCard.append(button('+ สร้างนโยบาย SLA', () => edit('สร้างนโยบาย SLA', [field('name', 'ชื่อนโยบาย SLA', 'text', {maxLength: 150})], {}, async body => {
      const created = await save('/admin/master-data/sla-policies', 'POST', body);
      await save(`/products/${product.id}/sla-policy`, 'PUT', {sla_policy_id: created.id});
    }, reload)));
  }
  if (current.sla_policy_id && user.can_edit_products) {
    const rules = await request(`/admin/master-data/sla-policies/${current.sla_policy_id}/rules`);
    if (version !== renderVersion || !user) return;
    const fields = [
      field('severity', 'ระดับความรุนแรง', 'select', {options: ['S1', 'S2', 'S3', 'S4'].map(value => ({value, label: value}))}),
      field('first_response_value', 'เวลาตอบกลับ', 'number', {number: true}),
      field('first_response_unit', 'หน่วยเวลาตอบกลับ', 'select', {options: ['MINUTES', 'HOURS', 'BUSINESS_DAYS'].map(value => ({value, label: value}))}),
      field('resolution_min_value', 'เวลาปิดเคสต่ำสุด', 'number', {number: true}),
      field('resolution_max_value', 'เวลาปิดเคสสูงสุด', 'number', {number: true}),
      field('resolution_unit', 'หน่วยเวลาปิดเคส', 'select', {options: ['MINUTES', 'HOURS', 'BUSINESS_DAYS'].map(value => ({value, label: value}))}),
      field('business_hours_only', 'นับเฉพาะเวลาทำการ', 'select', {boolean: true, default: true, options: [{value: true, label: 'ใช่'}, {value: false, label: 'ไม่ใช่'}]})
    ];
    const path = `/admin/master-data/sla-policies/${current.sla_policy_id}/rules`;
    policyCard.append(element('p', 'แก้ไขกฎมีผลกับทุกผลิตภัณฑ์ที่ใช้นโยบายเดียวกัน สร้างนโยบายใหม่หากต้องการแยกเฉพาะผลิตภัณฑ์', 'subtle'));
    policyCard.append(button('+ เพิ่มกฎ SLA', () => edit('เพิ่มกฎ SLA', fields, {}, body => save(path, 'POST', body), reload)));
    table(policyCard, [['ระดับ', r => r.severity], ['ตอบกลับ', r => `${r.first_response_value} ${r.first_response_unit}`], ['ปิดเคส', r => `${r.resolution_min_value}–${r.resolution_max_value} ${r.resolution_unit}`], ['สถานะ', r => badge(r.is_active)]], rules,
      r => [button('แก้ไขกฎ SLA', () => edit('แก้ไขกฎ SLA', [...fields, activeField], r, body => save(`${path}/${r.id}`, 'PATCH', body), reload))]);
  } else if (policy) {
    table(policyCard, [['ระดับ', r => r.severity], ['ตอบกลับ', r => `${r.first_response_value} ${r.first_response_unit}`], ['ปิดเคส', r => `${r.resolution_min_value}–${r.resolution_max_value} ${r.resolution_unit}`]], policy.rules);
  }
  for (const spec of [
    {path: 'symptoms', title: 'อาการ', values: options?.symptoms || [], maxLength: 150},
    {path: 'service-stages', title: 'ช่วงเวลาสอบ', values: options?.service_stages || [], maxLength: 100}
  ]) {
    const path = `/admin/master-data/${spec.path}`;
    const rows = user.can_edit_products ? await request(`${path}?product_id=${product.id}`) : spec.values;
    if (version !== renderVersion || !user) return;
    const fields = [field('name', `ชื่อ${spec.title}`, 'text', {maxLength: spec.maxLength}), activeField];
    if (spec.path === 'service-stages') fields.push(field('sort_order', 'ลำดับ', 'number', {number: true, default: 1}));
    const card = section(`หมวดหมู่: ${spec.title}`, `+ เพิ่ม${spec.title}`, () => edit(`เพิ่ม${spec.title}`, fields.filter(f => f.name !== 'is_active'), {},
      body => save(path, 'POST', {...body, product_id: product.id}), reload), user.can_edit_products);
    table(card, [['ชื่อ', row => row.name], ...(user.can_edit_products ? [['สถานะ', row => badge(row.is_active)]] : [])], rows,
      user.can_edit_products ? row => [button(`แก้ไข${spec.title}`, () => edit(`แก้ไข${spec.title}`, fields, row, body => save(`${path}/${row.id}`, 'PATCH', body), reload))] : null);
  }
  const modules = user.can_edit_products ? await request(`/products/${product.id}/modules?is_active=true`) : options?.modules || [];
  if (version !== renderVersion || !user) return;
  const problems = user.can_edit_products ? (await Promise.all(modules.map(module => request(`/admin/master-data/problem-types?module_id=${module.id}`)))).flat() : options?.problem_types || [];
  if (version !== renderVersion || !user) return;
  const fields = [field('name', 'ชื่อประเภทปัญหา', 'text', {maxLength: 100}), field('module_id', 'โมดูลของประเภทปัญหา', 'select', {number: true, options: modules.map(module => ({value: module.id, label: module.name}))})];
  const card = section('ประเภทปัญหาตามโมดูล', '+ เพิ่มประเภทปัญหา', () => edit('เพิ่มประเภทปัญหา', fields, {}, body => save('/admin/master-data/problem-types', 'POST', body), reload), user.can_edit_products && modules.length > 0);
  table(card, [['ชื่อ', row => row.name], ['โมดูล', row => modules.find(module => module.id === row.module_id)?.name || '—'], ...(user.can_edit_products ? [['สถานะ', row => badge(row.is_active)]] : [])], problems,
    user.can_edit_products ? row => [button('แก้ไขประเภทปัญหา', () => edit('แก้ไขประเภทปัญหา', [...fields, activeField], row, body => save(`/admin/master-data/problem-types/${row.id}`, 'PATCH', body), reload))] : null);
}

async function showCapture() {
  const heading = startView('สร้างเคส', 'บันทึกเรื่องก่อน แล้วค่อยเติมรายละเอียดภายหลัง · ข้อมูลขั้นต่ำ 3 ช่อง');
  heading.append(button('ยกเลิก', () => navigate('customers')));
  const card = section('ข้อมูลเริ่มต้น', '', null, false), wrap = element('div', null, 'autocomplete');
  const label = element('label', 'ลูกค้า / ผู้แจ้ง'), input = element('input'); input.setAttribute('aria-label', 'ค้นหาลูกค้า'); input.placeholder = 'ชื่อองค์กร / ผู้ติดต่อ / LINE / อีเมล / โทรศัพท์';
  label.append(input); const suggestions = element('div', null, 'suggestions'); suggestions.id = 'customer-choices'; suggestions.hidden = true;
  wrap.append(label, suggestions); card.append(wrap);
  const detail = element('div'); card.append(detail); let selected = null, selectionVersion = 0;
  const existing = element('div', null, 'existing-cases queue-table');
  let existingOrganization = null, existingGeneration = 0;
  card.addEventListener('customer-context-change', async event => {
    const organizationId = event.detail.organization_id;
    if (organizationId === existingOrganization) return;
    existingOrganization = organizationId; existing.replaceChildren();
    const generation = ++existingGeneration;
    if (!organizationId) return;
    try {
      const summary = await request(`${orgPath(organizationId)}/case-summary`);
      if (generation !== existingGeneration || !card.isConnected) return;
      existing.append(element('h3', `เคสเปิดของลูกค้ารายนี้ (${summary.open_count})`));
      if (!summary.open_count) { existing.append(element('p', 'ไม่มีเคสเปิดของลูกค้ารายนี้', 'muted')); return; }
      collection(existing, `/tickets?organization_id=${organizationId}&open_only=true`,
        [['เลขเคส', row => row.ticket_no], ['หัวข้อ', row => row.subject], ['สถานะ', row => row.status]],
        row => [button('เพิ่มเข้าเคสเดิม', () => showTicket(row.id))]);
    } catch (error) { if (generation === existingGeneration) failure(error); }
  });
  const formCard = section('บันทึกเคส', '', null, false), form = element('form'), optional = element('div', null, 'context-fields');
  const subjectLabel = element('label', 'หัวข้อเคส'), subject = element('input'); subject.maxLength = 255; subject.setAttribute('aria-label', 'หัวข้อเคส'); subjectLabel.append(subject);
  const channelLabel = element('label', 'ช่องทางแจ้ง'), channel = element('select'); channel.setAttribute('aria-label', 'ช่องทางแจ้ง');
  for (const [value, text] of [['', 'ยังไม่ระบุ'], ['line_oa', 'LINE OA'], ['line_group', 'LINE Group'], ['line_personal', 'LINE ส่วนตัว'], ['portal', 'Portal'], ['email', 'อีเมล'], ['phone', 'โทรศัพท์'], ['face_to_face', 'พบหน้า'], ['other', 'อื่น ๆ']]) {
    const option = element('option', text); option.value = value; channel.append(option);
  }
  channelLabel.append(channel);
  const descriptionLabel = element('label', 'รายละเอียดเคส'), description = element('textarea'); description.maxLength = 20000; description.setAttribute('aria-label', 'รายละเอียดเคส'); descriptionLabel.append(description);
  const submit = element('button', 'สร้างเคส', 'primary'); submit.type = 'submit'; submit.disabled = !user.can_create_cases;
  const result = element('div'); result.setAttribute('role', 'status');
  const channels = element('div', null, 'channel-options');
  channel.classList.add('channel-source'); channel.tabIndex = -1; channel.setAttribute('aria-hidden', 'true');
  for (const option of channel.options) {
    if (!option.value) continue;
    const choice = button(option.textContent, () => { channel.value = option.value; channel.dispatchEvent(new Event('change')); });
    choice.dataset.channel = option.value; choice.setAttribute('aria-pressed', 'false'); channels.append(choice);
  }
  channelLabel.append(channels);
  const more = element('details', null, 'capture-optional'), moreTitle = element('summary', 'รายละเอียดเพิ่มเติม · เติมภายหลังได้');
  more.append(moreTitle, descriptionLabel, optional);
  form.append(subjectLabel, channelLabel, existing, more, result); card.append(form); formCard.remove();
  const footer = element('footer', null, 'capture-footer'), completion = element('p'), actions = element('div', null, 'actions');
  let saveDraft = false, saving = false;
  const draftButton = button('บันทึกเป็นร่าง', () => { saveDraft = true; form.requestSubmit(); }); draftButton.disabled = !user.can_create_cases;
  submit.setAttribute('form', 'capture-form'); form.id = 'capture-form';
  actions.append(draftButton, submit); footer.append(completion, actions); workspace.append(footer);
  const preview = element('section', null, 'card capture-preview'), previewData = element('dl'), previewState = element('span', 'ยังไม่สร้าง', 'preview-state');
  preview.append(element('h2', 'ตัวอย่างเคส'), previewState, previewData);
  const updatePreview = () => {
    previewData.replaceChildren();
    for (const [name, value] of [['เลขที่เคส', 'ระบบออกเลขหลังสร้าง'], ['ลูกค้า / ผู้แจ้ง', selected ? input.value : 'ยังไม่เลือก'], ['หัวข้อ', subject.value.trim() || 'ยังไม่ระบุ'], ['ช่องทาง', channel.selectedOptions[0]?.textContent || 'ยังไม่ระบุ']]) {
      previewData.append(element('dt', name), element('dd', value));
    }
    const complete = !!selected && !!subject.value.trim() && !!channel.value;
    previewState.textContent = complete ? 'พร้อมสร้าง · ยังไม่บันทึก' : 'ข้อมูลยังไม่ครบ · ยังไม่บันทึก';
    completion.textContent = complete ? 'ข้อมูลขั้นต่ำครบ 3 ช่อง พร้อมสร้างเคส' : 'เลือกลูกค้า / ผู้แจ้ง หัวข้อ และช่องทาง เพื่อสร้างเคส';
    submit.disabled = !user.can_create_cases || !complete || saving;
    draftButton.disabled = !user.can_create_cases || saving;
    channels.querySelectorAll('button').forEach(node => { const active = node.dataset.channel === channel.value; node.classList.toggle('selected', active); node.setAttribute('aria-pressed', String(active)); });
  };
  form.addEventListener('input', updatePreview); channel.addEventListener('change', updatePreview);
  card.addEventListener('customer-context-change', updatePreview);

  let optionsVersion = 0, optionsInstance = null, caseSelection = {}, loadingOptions = false;
  card.addEventListener('customer-context-change', async event => {
    const instanceId = event.detail.product_instance_id;
    if (instanceId === optionsInstance) return;
    optionsInstance = instanceId; caseSelection = {}; optional.replaceChildren();
    const generation = ++optionsVersion; loadingOptions = !!instanceId;
    if (!instanceId) return;
    try {
      const instance = await request(`/product-instances/${instanceId}`);
      const options = await request(`/products/${instance.product_id}/case-options`);
      if (generation !== optionsVersion || !card.isConnected) return;
      const selectors = {};
      for (const [name, title, items] of [['module_id', 'โมดูลของเคส', options.modules], ['category_id', 'ประเภทปัญหาของเคส', options.problem_types], ['symptom_id', 'อาการของเคส', options.symptoms], ['service_stage_id', 'ช่วงบริการของเคส', options.service_stages]]) {
        const label = element('label', title), select = element('select'); select.setAttribute('aria-label', title); selectors[name] = select;
        const populate = rows => {
          select.replaceChildren(); const empty = element('option', 'ยังไม่ระบุ'); empty.value = ''; select.append(empty);
          rows.forEach(row => { const option = element('option', row.name); option.value = row.id; select.append(option); });
        };
        populate(name === 'category_id' ? [] : items);
        select.addEventListener('change', () => {
          caseSelection[name] = select.value ? Number(select.value) : null;
          if (name === 'module_id') {
            caseSelection.category_id = null;
            const categories = selectors.category_id; categories.replaceChildren(); const empty = element('option', 'ยังไม่ระบุ'); empty.value = ''; categories.append(empty);
            options.problem_types.filter(row => row.module_id === caseSelection.module_id).forEach(row => { const option = element('option', row.name); option.value = row.id; categories.append(option); });
          }
        }); label.append(select); optional.append(label);
      }
    } catch (error) { if (generation === optionsVersion) failure(error); }
    finally { if (generation === optionsVersion) loadingOptions = false; }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const draftRequested = saveDraft; saveDraft = false;
    if (saving) return;
    if (loadingOptions) { notify('รอโหลดหมวดหมู่ของผลิตภัณฑ์ก่อนบันทึก', true); return; }
    saving = true;
    submit.disabled = true; draftButton.disabled = true;
    try {
      const ticket = await request('/tickets', {method: 'POST', body: {...selected, ...caseSelection,
        subject: subject.value, channel: channel.value || null, description: description.value, save_as_draft: draftRequested}});
      if (!form.isConnected) return;
      result.replaceChildren(element('p', `บันทึก ${ticket.status}: ${ticket.ticket_no || `ร่าง #${ticket.id}`}`), button('ดูเคสที่บันทึก', () => showTicket(ticket.id)));
      subject.value = ''; description.value = '';
    } catch (error) { failure(error); }
    finally { saving = false; saveDraft = false; if (user && form.isConnected) updatePreview(); }
  });
  const clear = () => {
    ++selectionVersion; selected = null; detail.replaceChildren(); more.querySelectorAll('[data-customer-fields]').forEach(node => node.remove());
    card.dispatchEvent(new CustomEvent('customer-context-change', {detail: {
      organization_id: null, contact_id: null, product_instance_id: null,
      department_id: null, course_or_exam_id: null,
    }, bubbles: true}));
  };
  disposePicker = mountCustomerAutocomplete(input, suggestions, request, async choice => {
    const current = ++selectionVersion;
    try {
      const context = await request(`${orgPath(choice.organization.id)}/selection-context${choice.contact ? `?contact_id=${choice.contact.id}` : ''}`);
      if (current !== selectionVersion || !card.isConnected) return;
      selected = {organization_id: context.organization.id, contact_id: context.contact?.id || null, product_instance_id: context.instances.length === 1 ? context.instances[0].id : null, department_id: null, course_or_exam_id: null};
      detail.replaceChildren(element('p', `${context.organization.name}${context.contact ? ` · ${context.contact.name}` : ''}`, 'selected-customer'));
      more.querySelectorAll('[data-customer-fields]').forEach(node => node.remove());
      const fields = element('div', null, 'context-fields'); fields.dataset.customerFields = 'true';
      const draw = () => { card.dispatchEvent(new CustomEvent('customer-context-change', {detail: {...selected}, bubbles: true})); };
      for (const spec of [
        {name: 'product_instance_id', label: 'ระบบที่ลูกค้าใช้งาน', items: context.instances, text: i => `${i.name} · ${i.version} · ${i.environment}`},
        {name: 'department_id', label: 'หน่วยงาน', items: context.departments, text: i => i.name},
        {name: 'course_or_exam_id', label: 'รายวิชา / การสอบ', items: context.courses, text: i => `${i.name} (${i.kind === 'course' ? 'รายวิชา' : 'การสอบ'})`}
      ]) {
        const label = element('label', spec.label), select = element('select'); select.name = spec.name; select.setAttribute('aria-label', spec.label);
        const empty = element('option', spec.items.length ? 'เลือกจากทะเบียน' : 'ยังไม่มีข้อมูลในทะเบียน'); empty.value = ''; select.append(empty);
        for (const item of spec.items) { const option = element('option', spec.text(item)); option.value = item.id; select.append(option); }
        select.value = selected[spec.name] || '';
        select.addEventListener('change', () => { selected[spec.name] = select.value ? Number(select.value) : null; draw(); }); label.append(select); fields.append(label);
      }
      more.prepend(fields); draw();
    } catch (error) { if (current === selectionVersion) failure(error); }
  }, failure, clear);
  const layout = element('div', null, 'capture-layout'), mainColumn = element('div', null, 'capture-main');
  mainColumn.append(card); layout.append(mainColumn, preview); workspace.append(layout); updatePreview();

}
async function navigate(view) {
  if (!user) return;
  currentView = view;
  document.querySelectorAll('[data-view]').forEach(node => node.classList.toggle('active', node.dataset.view === view));
  document.querySelector('#breadcrumb').textContent = {customers: 'Customers', products: 'Product Registry', capture: 'สร้างเคส', work: 'งานของฉัน', cases: 'เคสทั้งหมด', unassigned: 'ยังไม่มีผู้รับ'}[view];
  await ({customers: showCustomers, products: showProducts, capture: showCapture, work: () => showQueue('work'), cases: () => showQueue('cases'), unassigned: () => showQueue('unassigned')}[view])();
}
function signOut() {
  ++renderVersion;
  token = ''; user = null; disposePicker?.(); disposePicker = null; dialog.close();
  workspace.hidden = true; workspace.replaceChildren(); document.querySelector('#login-panel').hidden = false;
  document.querySelector('#logout').hidden = true; document.querySelector('#new-case').hidden = true; document.querySelector('#user-label').textContent = '';
  document.querySelector('#product-navigation').replaceChildren();
  document.querySelectorAll('.admin-navigation').forEach(node => { node.hidden = true; });
}
document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = event.currentTarget, submit = form.querySelector('button'); submit.disabled = true;
  try {
    const data = await request('/auth/login', {method: 'POST', body: new URLSearchParams(new FormData(form))});
    token = data.access_token; user = await request('/registry/session'); form.reset();
    document.querySelector('#login-panel').hidden = true; workspace.hidden = false; document.querySelector('#logout').hidden = false;
    document.querySelector('#user-label').textContent = `${user.username} · ${user.role}`;
    document.querySelector('#sidebar-initials').textContent = user.username.slice(0, 2).toUpperCase();
    document.querySelector('#sidebar-account').replaceChildren(element('strong', user.username), element('small', user.role));
    document.querySelector('#new-case').hidden = !user.can_create_cases;
    document.querySelectorAll('.admin-navigation').forEach(node => { node.hidden = !user.can_edit_products; });
    await refreshProductNavigation();
    document.querySelector('#notice').hidden = true; await navigate(currentView);
  } catch (error) { signOut(); failure(error); } finally { submit.disabled = false; }
});
document.querySelector('#logout').addEventListener('click', signOut);
document.querySelectorAll('[data-view]').forEach(node => node.addEventListener('click', () => navigate(node.dataset.view).catch(failure)));
document.querySelector('#cancel-editor').addEventListener('click', () => dialog.close());
document.querySelector('#editor-form').addEventListener('submit', async event => {
  event.preventDefault(); const submit = document.querySelector('#save-editor'); submit.disabled = true;
  try { await saveAction(); } catch (error) { document.querySelector('#editor-error').textContent = error.message; }
  finally { submit.disabled = false; }
});

async function showTicket(id) {
  const version = renderVersion;
  const ticket = await request(`/tickets/${id}`);
  if (version !== renderVersion || !user) return;
  startView(ticket.ticket_no || `ร่าง #${ticket.id}`, ticket.subject || 'ยังไม่มีหัวข้อ');
  if (ticket.organization_id) workspace.prepend(button('← กลับลูกค้า', async () => showOrganization(await request(orgPath(ticket.organization_id)))));
  const card = section('รายละเอียดเคส', '', null, false);
  card.append(element('p', `สถานะ: ${ticket.status} · ช่องทาง: ${ticket.channel || 'ยังไม่ระบุ'}`),
    element('p', ticket.description || 'ยังไม่มีรายละเอียด'),
    element('p', `แจ้งเมื่อ: ${new Date(ticket.reported_at).toLocaleString('th-TH')}`));
}

async function refreshProductNavigation() {
  const products = await all('/products?is_active=true');
  const root = document.querySelector('#product-navigation'); root.replaceChildren();
  if (!user) return;
  for (const product of products) {
    const item = button(product.name, () => { currentView = 'products'; document.querySelectorAll('.nav').forEach(node => node.classList.remove('active')); item.classList.add('active'); document.querySelector('#breadcrumb').textContent = product.name; return showProduct(product); }, 'nav');
    item.setAttribute('aria-label', `ผลิตภัณฑ์ ${product.name}`); root.append(item);
  }
}
document.querySelector('#new-case').addEventListener('click', () => navigate('capture').catch(failure));
document.querySelector('#toggle-sidebar').addEventListener('click', () => {
  const mobile = window.matchMedia('(max-width:800px)').matches;
  document.body.classList.toggle(mobile ? 'mobile-menu-open' : 'sidebar-collapsed');
  document.querySelector('#toggle-sidebar').setAttribute('aria-expanded', String(mobile ? document.body.classList.contains('mobile-menu-open') : !document.body.classList.contains('sidebar-collapsed')));
});

async function showQueue(view) {
  const title = {work: 'งานของฉัน', cases: 'เคสทั้งหมด', unassigned: 'ยังไม่มีผู้รับผิดชอบ'}[view];
  const heading = startView(title, view === 'work' ? 'ดูเคสที่ต้องดำเนินการและเคสร่างของคุณ' : 'ค้นหาและเปิดดูเคสในระบบ');
  if (user.can_create_cases) heading.append(button('＋ สร้างเคส', () => navigate('capture'), 'primary'));
  const version = renderVersion;
  const summary = await request('/tickets/queue-summary');
  if (version !== renderVersion || !user) return;
  if (view === 'work') {
    const counts = element('div', null, 'action-counts');
    for (const [count, label, action] of [[summary.unassigned, 'ยังไม่มีผู้รับผิดชอบ', () => navigate('unassigned')], ['—', 'เหลือเวลา SLA ไม่ถึง 25%', null], [summary.mine, 'งานของฉันที่เปิดอยู่', () => loadQueue({mine: true})], [summary.today, 'เคสเข้าใหม่วันนี้', () => loadQueue({today_only: true})]]) {
      const item = button('', action || (() => {}), 'action-count'); item.append(element('strong', count), element('span', label)); item.disabled = !action; counts.append(item);
    }
    workspace.append(counts);
  }
  const card = section(view === 'cases' ? 'รายการเคส' : 'คิวเคสที่เปิดอยู่', '', null, false);
  const controls = element('div', null, 'toolbar');
  controls.append(button('ทั้งหมด', () => loadQueue({})), button('งานของฉัน', () => loadQueue({mine: true})), button('ยังไม่มีผู้รับ', () => loadQueue({unassigned: true})));
  card.append(controls, element('p', 'เรียงตามเวลาบันทึกล่าสุด · ยังไม่มีข้อมูลเวลา SLA สำหรับจัดลำดับ', 'queue-note'));
  const searchForm = element('form', null, 'queue-search'), search = element('input'), searchButton = element('button', 'ค้นหา');
  search.placeholder = 'ค้นหาเลขเคสหรือหัวข้อ'; search.setAttribute('aria-label', 'ค้นหาเคส'); searchButton.type = 'submit'; searchForm.append(search, searchButton); card.append(searchForm);
  const results = element('div', null, 'queue-table'); card.append(results);
  let offset = 0, filters = view === 'unassigned' ? {unassigned: true} : {}, generation = 0;
  searchForm.addEventListener('submit', event => { event.preventDefault(); offset = 0; draw().catch(failure); });
  async function loadQueue(next) { filters = next; offset = 0; await draw(); }
  async function draw() {
    const current = ++generation;
    results.replaceChildren(); for (let i = 0; i < 4; i++) results.append(element('div', null, 'skeleton'));
    try {
      const params = new URLSearchParams({offset, limit: 26, ...filters});
      if (view !== 'cases') params.set('open_only', 'true');
      if (search.value.trim()) params.set('q', search.value.trim());
      const rows = await request(`/tickets?${params}`);
      const orgIds = [...new Set(rows.map(row => row.organization_id).filter(Boolean))];
      const organizations = new Map(await Promise.all(orgIds.map(async id => [id, (await request(orgPath(id))).name])));
      const instanceIds = [...new Set(rows.map(row => row.product_instance_id).filter(Boolean))];
      const productNames = new Map(await Promise.all(instanceIds.map(async id => { const instance = await request(`/product-instances/${id}`); return [id, (await request(`/products/${instance.product_id}`)).name]; })));
      if (current !== generation || version !== renderVersion || !user) return;
      results.replaceChildren();
      table(results, [['Case / Subject', row => { const link = button('', () => showTicket(row.id), 'link queue-subject'); link.append(element('small', row.ticket_no || `ร่าง #${row.id}`), element('strong', row.subject || 'ยังไม่มีหัวข้อ')); return link; }],
        ['Customer', row => organizations.get(row.organization_id) || 'ยังไม่ระบุ'], ['Priority', row => { const priority = element('span', row.severity || 'ยังไม่ระบุ'); if (row.severity === 'S1') priority.className = 'priority-critical'; return priority; }],
        ['Product', row => productNames.get(row.product_instance_id) || 'ยังไม่ระบุ'], ['Status', row => row.status], ['Channel', row => ({phone: 'โทรศัพท์', face_to_face: 'พบหน้า', email: 'อีเมล', line_oa: 'LINE OA', line_group: 'LINE Group', line_personal: 'LINE ส่วนตัว', portal: 'Portal', other: 'อื่น ๆ'}[row.channel] || '—')], ['Tier', row => row.current_tier === null ? '—' : `Tier ${row.current_tier}`], ['SLA', () => 'ยังไม่มีข้อมูล'], ['Assignee', row => row.assignee_id === user.id ? user.username : row.assignee_id ? 'มีผู้รับผิดชอบ' : 'ยังไม่มีผู้รับ']
      ], rows.slice(0, 25));
      const pager = element('div', null, 'pager');
      const prev = button('ก่อนหน้า', () => { offset -= 25; return draw(); }); prev.disabled = offset === 0;
      const next = button('ถัดไป', () => { offset += 25; return draw(); }); next.disabled = rows.length <= 25;
      pager.append(prev, element('span', rows.length ? `${offset + 1}–${offset + Math.min(25, rows.length)}` : '0 รายการ'), next); results.append(pager);
    } catch (error) {
      if (current !== generation || version !== renderVersion) return;
      const errorBox = element('div', null, 'error-inline'); errorBox.append(element('p', 'ไม่สามารถโหลดคิวเคสได้'), button('ลองอีกครั้ง', draw)); results.replaceChildren(errorBox);
    }
  }
  await draw();
  if (view === 'work' && version === renderVersion && user) {
    const drafts = section(`เคสร่างของคุณ (${summary.drafts})`, '', null, false);
    collection(drafts, '/tickets?drafts_only=true', [['หัวข้อ', row => row.subject || 'ยังไม่มีหัวข้อ'], ['สร้างเมื่อ', row => new Date(row.created_at).toLocaleString('th-TH')]], row => [button('ดูร่าง', () => showTicket(row.id))]);
  }
}

document.querySelectorAll('.nav[data-view]').forEach(node => node.setAttribute('aria-label', node.querySelector('span').textContent));
