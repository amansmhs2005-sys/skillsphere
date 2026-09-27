import axios from "axios";

const client = axios.create({ baseURL: "/api" });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("skillsphere_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Extract a readable message from a Flask JSON error response.
export function apiErrorMessage(err) {
  return err?.response?.data?.error || err.message || "Something went wrong";
}

export default client;
