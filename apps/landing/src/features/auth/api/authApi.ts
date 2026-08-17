import { apiClient } from '../../../infrastructure/api/client';
import type { AuthUser } from '../store/authStore';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface APIResponse<T> {
  data: T;
  message?: string;
}

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const response = await apiClient.post<APIResponse<TokenResponse>>('/auth/login', { email, password });
    return response.data.data;
  },
  
  getMe: async (): Promise<AuthUser> => {
    const response = await apiClient.get<APIResponse<AuthUser>>('/auth/me');
    return response.data.data;
  }
};
