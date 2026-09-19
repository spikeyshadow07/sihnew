export async function request(path, options = {}) {
  const response = await fetch('/api' + path, options);
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message = Array.isArray(payload.detail) ? payload.detail.map(e => e.msg).join('; ') : (payload.detail || message);
    } catch {}
    throw new Error(message || 'The request failed.');
  }
  return response.json();
}
export const postJSON = (path, body) => request(path, {
  method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
});
