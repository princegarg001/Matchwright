import { render, screen } from "@testing-library/react";
import { ResultView, modeLabel } from "../components/ResultView";
import { okResult } from "./fixtures";

describe("ResultView", () => {
  it("shows score, band, three reasons and grouped requirements", () => {
    render(<ResultView result={okResult} />);
    expect(screen.getByTestId("score")).toHaveTextContent("74");
    expect(screen.getByText("Good fit")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").filter((li) => li.className.includes("border-l-2"))).toHaveLength(3);
    expect(screen.getByText("Must have")).toBeInTheDocument();
    expect(screen.getByText("Not found in resume")).toBeInTheDocument();
    expect(screen.getByText(/2 of 3 met/)).toBeInTheDocument();
    expect(screen.getByText("Preferred")).toBeInTheDocument();
  });

  it("renders the knowledge graph built during this match", () => {
    render(<ResultView result={okResult} />);
    expect(screen.getByText("Knowledge graph")).toBeInTheDocument();
    expect(screen.getByText("Resume")).toBeInTheDocument();
    expect(screen.getByText("74 / 100")).toBeInTheDocument();
  });

  it("shows the fallback message instead of a score", () => {
    render(<ResultView result={{ ...okResult, status: "insufficient_information", score: null,
      message: "I don't have enough information to score this match: too short.", hint: "Paste the full resume." }} />);
    expect(screen.queryByTestId("score")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("I don't have enough information");
  });

  it("labels run modes in plain words", () => {
    expect(modeLabel("agent")).toBe("Agent ran every step");
    expect(modeLabel("offline+cache")).toBe("Offline mode, no language model (from cache)");
    expect(modeLabel("live_graph")).toBe("Ran step by step for the live graph view");
  });
});
