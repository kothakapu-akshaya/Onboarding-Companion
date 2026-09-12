import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import "@testing-library/jest-dom";
import ProgressCard from "../components/ProgressCard";

describe("ProgressCard Component", () => {
  it("displays completed percentage correctly", () => {
    render(<ProgressCard totalTasks={10} completedTasks={7} />);

    expect(screen.getByText("70% Completed")).toBeInTheDocument();
  });

  it("displays task information", () => {
    render(<ProgressCard totalTasks={5} completedTasks={2} />);

    expect(screen.getByText("Total Tasks")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("handles zero total tasks without dividing by zero", () => {
    render(<ProgressCard totalTasks={0} completedTasks={0} />);

    expect(screen.getByText("0% Completed")).toBeInTheDocument();
  });

  it("caps progress at 100% for full completion", () => {
    render(<ProgressCard totalTasks={4} completedTasks={4} />);

    expect(screen.getByText("100% Completed")).toBeInTheDocument();
  });
});
