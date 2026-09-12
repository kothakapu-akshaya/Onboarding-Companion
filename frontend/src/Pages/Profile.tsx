import Layout from "../components/Layout";
import ProfileCard from "../components/ProfileCard";

import { useAuth } from "../context/auth";

function Profile() {
  const { user } = useAuth();

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
        phone={user.phone || ""}
        email={user.email || ""}
        profession={user.profession || undefined}
        organisation={user.organisation || undefined}
        currentYear={user.current_year_of_study || undefined}
        role={user.role || "Employee"}
      />
    </Layout>
  );
}

export default Profile;
