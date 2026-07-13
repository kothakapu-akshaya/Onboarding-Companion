import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import ProfileCard from "../components/ProfileCard";
import { getProfile } from "../services/user";

function Profile() {
  const [user, setUser] = useState<any>(null);

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
        role={user.role}
      />
    </Layout>
  );
}

export default Profile;