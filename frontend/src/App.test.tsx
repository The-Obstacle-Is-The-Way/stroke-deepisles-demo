import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "./mocks/server";
import { errorHandlers, setMockJobDuration } from "./mocks/handlers";
import App from "./App";

// Mock NiiVue to avoid WebGL in tests
vi.mock("@niivue/niivue", () => ({
  Niivue: class MockNiivue {
    attachToCanvas = vi.fn();
    loadVolumes = vi.fn().mockResolvedValue(undefined);
    cleanup = vi.fn();
    gl = {
      getExtension: vi.fn(() => ({ loseContext: vi.fn() })),
    };
    opts = {};
  },
}));

describe("App Integration", () => {
  // Use real timers for integration tests - fake timers don't sync well
  // with MSW's async handlers and polling intervals
  beforeEach(() => {
    // Reset mock job duration to fast for tests
    setMockJobDuration(500); // Jobs complete in 500ms
  });

  afterEach(() => {
    setMockJobDuration(500); // Reset to default
  });

  describe("Initial Render", () => {
    it("renders main heading", () => {
      render(<App />);

      expect(
        screen.getByRole("heading", { name: /stroke lesion segmentation/i }),
      ).toBeInTheDocument();
    });

    it("renders case selector", async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });
    });

    it("renders run button", () => {
      render(<App />);

      expect(
        screen.getByRole("button", { name: /run segmentation/i }),
      ).toBeInTheDocument();
    });

    it("shows placeholder viewer message", () => {
      render(<App />);

      expect(
        screen.getByText(/select a case and run segmentation/i),
      ).toBeInTheDocument();
    });
  });

  describe("Run Button State", () => {
    it("disables run button when no case selected", async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      expect(
        screen.getByRole("button", { name: /run segmentation/i }),
      ).toBeDisabled();
    });

    it("enables run button when case selected", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");

      expect(
        screen.getByRole("button", { name: /run segmentation/i }),
      ).toBeEnabled();
    });
  });

  describe("Segmentation Flow", () => {
    it("shows processing state when running", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      // Button should show "Processing..." while job is running
      expect(
        screen.getByRole("button", { name: /processing/i }),
      ).toBeInTheDocument();
    });

    it("shows progress indicator during job execution", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      // Progress indicator should appear during processing
      await waitFor(() => {
        expect(screen.getByRole("progressbar")).toBeInTheDocument();
      });
    });

    it("displays metrics after successful segmentation", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      // Wait for job to complete (mock duration is 500ms, polling is 2s)
      // Use 5s timeout to account for polling interval
      await waitFor(
        () => {
          expect(screen.getByText("0.847")).toBeInTheDocument();
        },
        { timeout: 5000 },
      );

      expect(screen.getByText("15.32 mL")).toBeInTheDocument();
    });

    it("displays viewer after successful segmentation", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      // Wait for job to complete and canvas to render
      await waitFor(
        () => {
          expect(document.querySelector("canvas")).toBeInTheDocument();
        },
        { timeout: 5000 },
      );
    });

    it("hides placeholder after successful segmentation", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      // Wait for job to complete
      await waitFor(
        () => {
          expect(screen.getByText("0.847")).toBeInTheDocument();
        },
        { timeout: 5000 },
      );

      expect(
        screen.queryByText(/select a case and run segmentation/i),
      ).not.toBeInTheDocument();
    });

    it("shows cancel button during processing", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("shows error when job creation fails", async () => {
      server.use(errorHandlers.segmentCreateError);
      const user = userEvent.setup();

      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });

      expect(screen.getByText(/failed to create job/i)).toBeInTheDocument();
    });

    it("allows retry after error", async () => {
      server.use(errorHandlers.segmentCreateError);
      const user = userEvent.setup();

      render(<App />);

      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByRole("combobox"), "sub-stroke0001");
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });

      // Reset to success handler
      server.resetHandlers();

      // Retry
      await user.click(
        screen.getByRole("button", { name: /run segmentation/i }),
      );

      // Wait for job to complete (real timer now)
      await waitFor(
        () => {
          expect(screen.getByText("0.847")).toBeInTheDocument();
        },
        { timeout: 5000 },
      );

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  describe("Multiple Runs", () => {
    it(
      "allows running segmentation on different cases",
      { timeout: 15000 },
      async () => {
        const user = userEvent.setup();
        render(<App />);

        await waitFor(() => {
          expect(screen.getByRole("combobox")).toBeInTheDocument();
        });

        // First case
        await user.selectOptions(
          screen.getByRole("combobox"),
          "sub-stroke0001",
        );
        await user.click(
          screen.getByRole("button", { name: /run segmentation/i }),
        );

        // Wait for first segmentation to complete - check metrics (Dice Score proves completion)
        await waitFor(
          () => {
            expect(screen.getByText("0.847")).toBeInTheDocument();
            // Button should no longer say "Processing..." after completion
            expect(
              screen.queryByRole("button", { name: /processing/i }),
            ).not.toBeInTheDocument();
          },
          { timeout: 5000 },
        );

        // Second case
        await user.selectOptions(
          screen.getByRole("combobox"),
          "sub-stroke0002",
        );
        await user.click(
          screen.getByRole("button", { name: /run segmentation/i }),
        );

        // Wait for second job to complete - check that case ID changed in metrics
        // Note: We look within the metrics container for the case ID to avoid matching dropdown
        await waitFor(
          () => {
            // The metrics panel shows case ID in a span with class "ml-2 font-mono"
            // after the "Case:" label
            const caseLabels = screen.getAllByText(/Case:/i);
            expect(caseLabels.length).toBeGreaterThan(0);
            // The second run should show sub-stroke0002 in the metrics
            const metricsContainer = screen.getByText("Results").closest("div");
            expect(metricsContainer).toHaveTextContent("sub-stroke0002");
          },
          { timeout: 5000 },
        );
      },
    );
  });
});
