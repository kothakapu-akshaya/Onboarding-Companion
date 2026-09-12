import api from "../api/axios";

import type { UserProfile } from "../types/user";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string | null;
  phone: string;
}

export const login = async (
  phone: string,
  password: string
): Promise<TokenResponse> => {
  const response = await api.post<TokenResponse>("/auth/login", {
    phone,
    password,
  });

  return response.data;
};

export const getCurrentUser = async (): Promise<UserProfile> => {
  const response = await api.get<UserProfile>("/auth/me");
  return response.data;
};
