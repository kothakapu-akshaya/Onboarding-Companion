import api from "../api/axios";

export type Task = {
  id: string;
  title: string;
  description: string;
  status: string;
  assigned_to: string;
  created_at: string;
};

export const getTasks = async (): Promise<Task[]> => {
  const response = await api.get("/tasks/");
  return response.data;
};
