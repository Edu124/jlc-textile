import axios from "axios";

const api = axios.create({ baseURL: "/" });

// Attach the saved token to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jlc_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, drop the token and bounce to login.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("jlc_token");
      if (!location.pathname.startsWith("/login")) location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;
