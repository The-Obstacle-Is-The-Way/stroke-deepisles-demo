import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary } from "../ErrorBoundary";

// Component that throws an error
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div>Normal content</div>;
}

describe("ErrorBoundary", () => {
  // Suppress React error boundary console.error in tests
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Child content</div>
      </ErrorBoundary>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("displays error UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(
      screen.getByText(/an unexpected error occurred/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("shows error details in expandable section", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Click to expand error details
    const details = screen.getByText("Error details");
    fireEvent.click(details);

    expect(screen.getByText("Test error message")).toBeInTheDocument();
  });

  it("resets error state when Try Again is clicked", () => {
    // Use a stateful wrapper to control whether child throws
    let shouldThrow = true;
    const StatefulThrower = () => {
      if (shouldThrow) {
        throw new Error("Test error");
      }
      return <div>Normal content</div>;
    };

    const { rerender } = render(
      <ErrorBoundary>
        <StatefulThrower />
      </ErrorBoundary>,
    );

    // Verify error state
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Fix the underlying issue before clicking retry
    shouldThrow = false;

    // Click Try Again - this resets ErrorBoundary state and re-renders children
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));

    // Force rerender to trigger new render after state reset
    rerender(
      <ErrorBoundary>
        <StatefulThrower />
      </ErrorBoundary>,
    );

    // Should show normal content now since shouldThrow is false
    expect(screen.getByText("Normal content")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    const customFallback = <div data-testid="custom-fallback">Custom error UI</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );

    expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    expect(screen.getByText("Custom error UI")).toBeInTheDocument();
    // Should not show default error UI
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });

  it("logs error to console when error is caught", () => {
    const consoleSpy = vi.spyOn(console, "error");

    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );

    // ErrorBoundary should have called console.error
    expect(consoleSpy).toHaveBeenCalled();
  });
});
