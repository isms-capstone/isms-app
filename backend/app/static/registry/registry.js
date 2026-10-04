import {mountCustomerAutocomplete} from './autocomplete.js';

const workspace = document.querySelector('#workspace');
const dialog = document.querySelector('#editor');
let token = '', user = null, currentView = 'customers', disposePicker = null, saveAction = null, renderVersion = 0;

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
    columns.forEach(([, value]) => { const td = element('td'), result = value(row); td.append(result instanceof Node ? result : document.createTextNode(String(result ?? '—'))); tr.append(td); });
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
    input.value = record?.[spec.name] ?? spec.default ?? '';
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
const orgPath = id => `/customers/organizations/${id}`;
const save = (path, method, body) => request(path, {method, body});

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
  const card = section('ผลิตภัณฑ์', '+ เพิ่มผลิตภัณฑ์', () => edit('เพิ่มผลิตภัณฑ์', codeFields, {}, body => save('/products', 'POST', body), reload), user.can_edit_products);
  reload = collection(card, '/products', [['ผลิตภัณฑ์', row => button(row.name, () => showProduct(row), 'link')], ['รหัส', row => row.code], ['จำนวนโมดูล', row => row.modules.length], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_products ? [button('แก้ไข', () => edit('แก้ไขผลิตภัณฑ์', codeFields, row, body => save(`/products/${row.id}`, 'PUT', body), reload))] : [], true);
}
async function showProduct(product) {
  startView(product.name, `รหัส ${product.code}`); workspace.prepend(button('← กลับทะเบียนผลิตภัณฑ์', showProducts));
  const version = renderVersion;
  const current = await request(`/products/${product.id}`), teams = await request('/registry/teams');
  if (version !== renderVersion || !user) return;
  const team = section('ทีมผู้รับผิดชอบเริ่มต้น', 'เลือกทีม', () => edit('ทีมผู้รับผิดชอบเริ่มต้น', [field('default_team_id', 'ทีม', 'select', {number: true, required: false, options: [{value: '', label: 'ยังไม่กำหนด'}, ...teams.map(t => ({value: t.id, label: t.name}))]})], current, body => save(`/products/${product.id}/default-team`, 'PUT', body), () => showProduct(product)), user.can_edit_products);
  team.append(element('p', teams.find(t => t.id === current.default_team_id)?.name || 'ยังไม่กำหนด', 'muted'));
  let reload;
  const card = section('โมดูลของผลิตภัณฑ์', '+ เพิ่มโมดูล', () => edit('เพิ่มโมดูล', codeFields, {}, body => save(`/products/${product.id}/modules`, 'POST', body), reload), user.can_edit_products);
  reload = collection(card, `/products/${product.id}/modules`, [['ชื่อ', row => row.name], ['รหัส', row => row.code], ['สถานะ', row => badge(row.is_active)]], row => user.can_edit_products ? [button('แก้ไข', () => edit('แก้ไขโมดูล', codeFields, row, body => save(`/products/${product.id}/modules/${row.id}`, 'PUT', body), reload))] : []);
}
async function showCapture() {
  startView('เลือกบริบทลูกค้า', 'ค้นหาจากองค์กร ผู้ติดต่อ หรือช่องทาง แล้วเติมข้อมูลจากทะเบียน');
  const card = section('ลูกค้าและผู้แจ้ง', '', null, false), wrap = element('div', null, 'autocomplete');
  const label = element('label', 'ค้นหาลูกค้า'), input = element('input'); input.placeholder = 'ชื่อองค์กร / ผู้ติดต่อ / LINE / อีเมล / โทรศัพท์';
  label.append(input); const suggestions = element('div', null, 'suggestions'); suggestions.id = 'customer-choices'; suggestions.hidden = true;
  wrap.append(label, suggestions); card.append(wrap);
  const detail = element('div'); card.append(detail); let selected = null, selectionVersion = 0;
  const clear = () => {
    ++selectionVersion; selected = null; detail.replaceChildren();
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
      detail.replaceChildren(element('p', `${context.organization.name}${context.contact ? ` · ${context.contact.name}` : ''}`));
      const fields = element('div', null, 'context-fields'), output = element('pre', null, 'context-output');
      const draw = () => { output.textContent = JSON.stringify(selected, null, 2); card.dispatchEvent(new CustomEvent('customer-context-change', {detail: {...selected}, bubbles: true})); };
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
      detail.append(fields, element('p', 'ข้อมูลที่เลือกสำหรับฟอร์มสร้างเคส', 'subtle'), output,
        element('p', 'หน้านี้เลือกบริบทจากทะเบียน ยังไม่สร้างเคสจนกว่าจะเชื่อมโมดูล CAP', 'muted')); draw();
    } catch (error) { if (current === selectionVersion) failure(error); }
  }, failure, clear);
}
async function navigate(view) {
  if (!user) return;
  currentView = view;
  document.querySelectorAll('[data-view]').forEach(node => node.classList.toggle('active', node.dataset.view === view));
  document.querySelector('#breadcrumb').textContent = {customers: 'Customers', products: 'Product Registry', capture: 'บริบทลูกค้า'}[view];
  await ({customers: showCustomers, products: showProducts, capture: showCapture}[view])();
}
function signOut() {
  ++renderVersion;
  token = ''; user = null; disposePicker?.(); disposePicker = null; dialog.close();
  workspace.hidden = true; workspace.replaceChildren(); document.querySelector('#login-panel').hidden = false;
  document.querySelector('#logout').hidden = true; document.querySelector('#user-label').textContent = '';
}
document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = event.currentTarget, submit = form.querySelector('button'); submit.disabled = true;
  try {
    const data = await request('/auth/login', {method: 'POST', body: new URLSearchParams(new FormData(form))});
    token = data.access_token; user = await request('/registry/session'); form.reset();
    document.querySelector('#login-panel').hidden = true; workspace.hidden = false; document.querySelector('#logout').hidden = false;
    document.querySelector('#user-label').textContent = `${user.username} · ${user.role}`;
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
