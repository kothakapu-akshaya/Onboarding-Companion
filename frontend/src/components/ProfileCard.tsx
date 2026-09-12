import "../styles/ProfileCard.css";

type ProfileCardProps = {
  name: string;
  phone: string;
  email: string;
  profession?: string;
  organisation?: string;
  currentYear?: string;
  role?: string;
};

function ProfileCard({
  name,
  phone,
  email,
  profession,
  organisation,
  currentYear,
  role,
}: ProfileCardProps) {
  return (
    <div className="profile-card">
      <div className="profile-avatar" aria-hidden="true">
        👤
      </div>

      <h2>{name}</h2>

      <div className="profile-info">
        <div className="info-row">
          <span>Name</span>
          <strong>{name}</strong>
        </div>

        <div className="info-row">
          <span>Phone Number</span>
          <strong>{phone}</strong>
        </div>

        <div className="info-row">
          <span>Email</span>
          <strong>{email}</strong>
        </div>

        <div className="info-row">
          <span>Profession</span>
          <strong>{profession || "N/A"}</strong>
        </div>

        <div className="info-row">
          <span>Organisation</span>
          <strong>{organisation || "N/A"}</strong>
        </div>

        <div className="info-row">
          <span>Current Year</span>
          <strong>{currentYear || "N/A"}</strong>
        </div>

        <div className="info-row">
          <span>Role</span>
          <strong>{role || "N/A"}</strong>
        </div>
      </div>
    </div>
  );
}

export default ProfileCard;
