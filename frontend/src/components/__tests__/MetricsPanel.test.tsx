import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricsPanel } from "../MetricsPanel";

describe("MetricsPanel", () => {
  const defaultMetrics = {
    caseId: "sub-stroke0001",
    diceScore: 0.847,
    volumeMl: 15.32,
    elapsedSeconds: 12.5,
  };

  it("renders results heading", () => {
    render(<MetricsPanel metrics={defaultMetrics} />);

    expect(
      screen.getByRole("heading", { name: /results/i }),
    ).toBeInTheDocument();
  });

  it("displays case ID", () => {
    render(<MetricsPanel metrics={defaultMetrics} />);

    expect(screen.getByText("sub-stroke0001")).toBeInTheDocument();
  });

  it("displays dice score with 3 decimal places", () => {
    render(<MetricsPanel metrics={defaultMetrics} />);

    expect(screen.getByText("0.847")).toBeInTheDocument();
  });

  it("displays volume in mL with 2 decimal places", () => {
    render(<MetricsPanel metrics={defaultMetrics} />);

    expect(screen.getByText("15.32 mL")).toBeInTheDocument();
  });

  it("displays elapsed time with 1 decimal place", () => {
    render(<MetricsPanel metrics={defaultMetrics} />);

    expect(screen.getByText("12.5s")).toBeInTheDocument();
  });

  it("hides dice score row when null", () => {
    render(<MetricsPanel metrics={{ ...defaultMetrics, diceScore: null }} />);

    expect(screen.queryByText(/dice score/i)).not.toBeInTheDocument();
  });

  it("hides volume row when null", () => {
    render(<MetricsPanel metrics={{ ...defaultMetrics, volumeMl: null }} />);

    expect(screen.queryByText(/volume/i)).not.toBeInTheDocument();
  });

  it("applies card styling", () => {
    render(<MetricsPanel metrics={defaultMetrics} />);

    const panel = screen.getByRole("heading", {
      name: /results/i,
    }).parentElement;
    expect(panel).toHaveClass("bg-gray-800", "rounded-lg");
  });
});
