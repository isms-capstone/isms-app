// Reusable customer picker for CAP. Keep the token in the caller's API function.
export function mountCustomerAutocomplete(input, list, request, onSelect, onError, onInput = () => {}) {
  let timer, controller, sequence = 0;
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false');
  input.setAttribute('aria-controls', list.id);
  list.setAttribute('role', 'listbox');
  const close = () => { list.replaceChildren(); list.hidden = true; input.setAttribute('aria-expanded', 'false'); };
  const dismiss = () => { clearTimeout(timer); ++sequence; controller?.abort(); close(); };
  const search = async () => {
    const current = ++sequence;
    controller?.abort();
    const q = input.value.trim();
    close();
    if (!q) return;
    controller = new AbortController();
    try {
      const choices = await request(`/customers/autocomplete?q=${encodeURIComponent(q)}`, {signal: controller.signal});
      if (current !== sequence) return;
      for (const choice of choices) {
        const button = document.createElement('button');
        button.type = 'button'; button.setAttribute('role', 'option');
        button.textContent = choice.organization.name;
        const subtitle = document.createElement('small');
        subtitle.textContent = choice.contact ? `ผู้ติดต่อ: ${choice.contact.name}` : 'องค์กรลูกค้า';
        button.append(subtitle);
        button.addEventListener('click', async () => {
          dismiss();
          input.value = choice.contact ? `${choice.organization.name} · ${choice.contact.name}` : choice.organization.name;
          try { await onSelect(choice); } catch (error) { onError(error); }
        });
        list.append(button);
      }
      if (!choices.length) {
        const message = document.createElement('p'); message.className = 'empty'; message.textContent = 'ไม่พบลูกค้า'; list.append(message);
      }
      list.hidden = false; input.setAttribute('aria-expanded', 'true');
    } catch (error) { if (error.name !== 'AbortError' && current === sequence) onError(error); }
  };
  const handleInput = () => { clearTimeout(timer); ++sequence; controller?.abort(); close(); onInput(); timer = setTimeout(search, 120); };
  const handleKey = (event) => {
    if (event.key === 'Escape') dismiss();
    if (event.key === 'ArrowDown') { event.preventDefault(); list.querySelector('button')?.focus(); }
  };
  const listKey = (event) => {
    const buttons = [...list.querySelectorAll('button')];
    const index = buttons.indexOf(document.activeElement);
    if (event.key === 'Escape') { dismiss(); input.focus(); }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); buttons[(index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length]?.focus();
    }
  };
  const outside = (event) => { if (event.target !== input && !list.contains(event.target)) dismiss(); };
  input.addEventListener('input', handleInput); input.addEventListener('keydown', handleKey);
  list.addEventListener('keydown', listKey); document.addEventListener('click', outside);
  return () => {
    clearTimeout(timer); ++sequence; controller?.abort();
    input.removeEventListener('input', handleInput); input.removeEventListener('keydown', handleKey);
    list.removeEventListener('keydown', listKey); document.removeEventListener('click', outside);
  };
}
