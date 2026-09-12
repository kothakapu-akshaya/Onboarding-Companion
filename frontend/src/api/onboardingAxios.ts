import axios from "axios";

const onboardingBaseUrl: string | undefined =
  import.meta.env.VITE_ONBOARDING_API_URL;

if (!onboardingBaseUrl) {
  console.error(
    "VITE_ONBOARDING_API_URL is not set. Onboarding API requests will target the current origin."
  );
}

export function handleUnauthorized(): void {
  localStorage.removeItem("token");

  if (window.location.pathname !== "/") {
    window.location.href = "/";
  }
}

const onboardingApi = axios.create({
  baseURL: onboardingBaseUrl,
});

onboardingApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

onboardingApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      handleUnauthorized();
    }

    return Promise.reject(error);
  }
);

export default onboardingApi;