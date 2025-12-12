import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Layout } from "../Layout";

describe("Layout", () => {
  it("renders header with title", () => {
    render(<Layout>Content</Layout>);

    expect(
      screen.getByRole("heading", { name: /stroke lesion segmentation/i }),
    ).toBeInTheDocument();
  });

  it("renders subtitle", () => {
    render(<Layout>Content</Layout>);

    expect(screen.getByText(/deepisles segmentation/i)).toBeInTheDocument();
  });

  it("renders children in main area", () => {
    render(
      <Layout>
        <div data-testid="child">Test Child</div>
      </Layout>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("has accessible landmark structure", () => {
    render(<Layout>Content</Layout>);

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("applies dark theme styling", () => {
    render(<Layout>Content</Layout>);

    const container = screen.getByRole("banner").parentElement;
    expect(container).toHaveClass("bg-gray-950");
  });
});
