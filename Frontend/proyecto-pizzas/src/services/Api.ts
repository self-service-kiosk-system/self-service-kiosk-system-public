const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function getData(endpoint: string) {
  const res = await fetch(`${API_URL}/${endpoint}`, { headers: { "Content-Type": "application/json" } });

  if (!res.ok) throw new Error((await res.json()).detail || "GET error");
  
  return res.json();
}

async function postData(endpoint: string, payload: unknown) {
  const res = await fetch(`${API_URL}/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) throw new Error((await res.json()).detail || "POST error");

  return res.json();
}

async function putData(endpoint: string, payload: unknown) {
  const res = await fetch(`${API_URL}/${endpoint}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) throw new Error((await res.json()).detail || "PUT error");
  const text = await res.text();

  return text ? JSON.parse(text) : null;
}

async function deleteData(endpoint: string, payload?: unknown) {
  const res = await fetch(`${API_URL}/${endpoint}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : null,
  });

  if (!res.ok) throw new Error((await res.json()).detail || "DELETE error");
  const text = await res.text();

  return text ? JSON.parse(text) : null;
}

export default { getData, postData, putData, deleteData };