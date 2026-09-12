export type OnboardingTask = {
  id: number;
  title: string;
  description: string;
  category?: string;
};

export const onboardingTasks: OnboardingTask[] = [
  {
    id: 1,
    title: "Install Linux Environment",
    description:
      "Install a supported FOSS Linux distribution such as Debian, Arch Linux or Fedora as your primary operating system. Windows is not accepted for this internship.",
    category: "System Setup",
  },
  {
    id: 2,
    title: "Configure Git & GitLab",
    description:
      "Create a professional account on code.swecha.org and configure your Git identity (user.name and user.email) using the same email you registered with.",
    category: "Git & GitLab",
  },
  {
    id: 3,
    title: "Setup Docker",
    description:
      "Install Docker Engine and Docker Compose, enable and start the docker service, and add your user to the docker group. Verify with `docker run hello-world`.",
    category: "System Setup",
  },
  {
    id: 4,
    title: "Install Development Tools",
    description:
      "Install the required development tools from the workbench guide including git, curl, wget, openssh, gnupg2, lsb-release, and a FOSS code editor such as VS Code.",
    category: "System Setup",
  },
  {
    id: 5,
    title: "Verify Development Environment",
    description:
      "Verify that all required software is installed and accessible: git, python3, node, uv, docker, and the shell prompt all return version numbers without errors.",
    category: "System Setup",
  },
  {
    id: 6,
    title: "Update System and Install Essential Packages",
    description:
      "Update your package lists and upgrade your system using your distribution's package manager (apt, pacman or dnf), then add git, curl, wget, openssh, gnupg2 and lsb-release.",
    category: "System Setup",
  },
  {
    id: 7,
    title: "Set Up SSH Keys and Connect to GitLab",
    description:
      "Generate an ed25519 SSH key, add it to your GitLab account, and confirm the connection with `ssh -T git@code.swecha.org` returning the welcome message.",
    category: "Git & GitLab",
  },
  {
    id: 8,
    title: "Create a GitLab Profile README",
    description:
      "Create a public project named after your username and add a README.md with About, Tech Skills, Projects, Certifications and Aspirations sections.",
    category: "Git & GitLab",
  },
  {
    id: 9,
    title: "Clone a Repository Using SSH",
    description:
      "Clone a repository from code.swecha.org using its SSH URL (git@code.swecha.org:...) instead of HTTPS, and open the project locally.",
    category: "Git & GitLab",
  },
  {
    id: 10,
    title: "Make a Conventional Commit",
    description:
      "Make your first commit following the Conventional Commits format, e.g. `feat: add user authentication with JWT`, with a meaningful message body.",
    category: "Git & GitLab",
  },
  {
    id: 11,
    title: "Set Up GitLab CLI (glab)",
    description:
      "Install the official GitLab CLI, authenticate against code.swecha.org with `glab auth login --hostname code.swecha.org`, and confirm with `glab auth status`.",
    category: "Git & GitLab",
  },
  {
    id: 12,
    title: "Set Up GitLab Orbit Local",
    description:
      "Install GitLab Orbit Local, index a repository with `orbit index .`, and run a successful graph query such as `orbit sql 'SELECT count(*) FROM gl_definition'`.",
    category: "Git & GitLab",
  },
  {
    id: 13,
    title: "Set Up AI Coding Tools",
    description:
      "Install opencode, your primary AI coding agent, and the Ollama local AI runtime. Pull a model with `ollama pull llama3` and confirm both tools run.",
    category: "AI & Tooling",
  },
  {
    id: 14,
    title: "Set Up Terminal and Utilities",
    description:
      "Install the Starship prompt and add it to your shell config, then install Bruno for API testing and DuckDB for analytics.",
    category: "AI & Tooling",
  },
  {
    id: 15,
    title: "Contribute to the Swecha Corpus",
    description:
      "Sign up on corpus.swecha.org with your phone number and complete OTP verification, then submit at least one text contribution to the Telugu corpus.",
    category: "Swecha Ecosystem",
  },
  {
    id: 16,
    title: "Add the FSMI F-Droid Repository",
    description:
      "Install the F-Droid client, add the FSMI repository (https://apps.fsmi.in/fdroid/repo/) and confirm the Swecha Telugu Corpus app appears in the listings.",
    category: "Swecha Ecosystem",
  },
];
