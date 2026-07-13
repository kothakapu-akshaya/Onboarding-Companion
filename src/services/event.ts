import api from "../api/axios";

export const getEvents = async () => {
  const response = await api.get("/events");
  return response.data;
};