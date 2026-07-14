import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import "@testing-library/jest-dom";
import ProgressCard from "../components/ProgressCard";

describe("ProgressCard Component", () => {
  it("displays completed percentage correctly", () => {
    render(
      <ProgressCard totalTasks={10} completedTasks={7} upcomingEvents={2} />
    );

    expect(screen.getByText("70% Completed")).toBeInTheDocument();
  });

  it("displays task information", () => {
    render(
      <ProgressCard totalTasks={5} completedTasks={2} upcomingEvents={1} />
    );

    expect(screen.getByText("Assigned Tasks")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
