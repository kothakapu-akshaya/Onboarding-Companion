import api from "../api/axios";

export const login = async (phone: string, password: string) => {
  const response = await api.post("/auth/login", {
    phone,
    password,
  });

  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};
