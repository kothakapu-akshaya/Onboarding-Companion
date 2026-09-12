import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import "@testing-library/jest-dom";
import TaskCard from "../components/TaskCard";

function renderTask(status: string) {
  render(
    <MemoryRouter>
      <TaskCard id={1} title="Set up laptop" status={status} />
    </MemoryRouter>
  );
}

describe("TaskCard Component", () => {
  it("shows Start for a pending task", () => {
    renderTask("Pending");

    expect(screen.getByText("Set up laptop")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeInTheDocument();
  });

  it("shows View for a completed task", () => {
    renderTask("Completed");

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument();
  });
});
