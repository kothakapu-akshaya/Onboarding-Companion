export type OnboardingTask = {
  id: number;
  title: string;
  description: string;
};

export const onboardingTasks: OnboardingTask[] = [
  {
    id: 1,
    title: "Install Linux Environment",
    description: "Install a supported Linux distribution such as Debian, Ubuntu or Arch Linux.",
  },
  {
    id: 2,
    title: "Configure Git & GitLab",
    description: "Create your GitLab account and configure Git with your identity.",
  },
  {
    id: 3,
    title: "Setup Docker",
    description: "Install Docker and verify that it is running correctly.",
  },
  {
    id: 4,
    title: "Install Development Tools",
    description: "Install the required development tools mentioned in the workbench guide.",
  },
  {
    id: 5,
    title: "Verify Development Environment",
    description: "Verify that all required software has been installed successfully.",
  },
];