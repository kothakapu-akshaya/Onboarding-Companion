export interface UserProfile {
  id: string;
  username: string;
  name: string;
  phone: string | null;
  email: string | null;
  profession?: string | null;
  organisation?: string | null;
  current_year_of_study?: string | null;
  role?: string | null;
  roles?: string[];
}
