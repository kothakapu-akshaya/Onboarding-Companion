import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import ProfileCard from "../components/ProfileCard";
import { getProfile } from "../services/user";

type UserProfile = {
  name: string;
  phone: string;
  email: string;
  profession?: string;
  organisation?: string;
  current_year_of_study?: string;
  role?: string;
};

function Profile() {
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await getProfile();
        setUser(data);
      } catch (error) {
        console.error("Failed to fetch profile", error);
      }
    };

    fetchProfile();
  }, []);

  if (!user) {
    return (
      <Layout>
        <h2>Loading...</h2>
      </Layout>
    );
  }

  return (
    <Layout>
      <h1>My Profile</h1>

      <br />

      <ProfileCard
        name={user.name}
        phone={user.phone}
        email={user.email}
        profession={user.profession}
        organisation={user.organisation}
        currentYear={user.current_year_of_study}
        role={user.role || "Employee"}
      />
    </Layout>
  );
}

export default Profile;
