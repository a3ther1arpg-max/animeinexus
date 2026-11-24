import { QueryClient } from "@tanstack/react-query";
import { createRouter, rootRouteId } from "@tanstack/react-router";
import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SCREEN_IMAGES } from "@/game/fighterAssets";
import { CharacterPicker } from "@/routes/index";
import { routeTree } from "@/routeTree.gen";

// Match routes without running loaders or rendering: loaders may need a server or
// network the test run lacks, and jsdom never loads the stylesheets React waits on.
describe("App routing", () => {
  it("matches a page for / instead of falling back to not found", () => {
    const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });

    const matches = router.matchRoutes("/");

    expect(matches.at(-1)?.routeId).not.toBe(rootRouteId);
  });
});

describe("Character selection", () => {
  it("uses the supplied highlight artwork for each fighter", () => {
    const view = render(<CharacterPicker onPick={() => {}} />);
    const image = view.container.querySelector("img");

    fireEvent.click(view.getByRole("button", { name: "NARUTO" }));
    expect(image?.getAttribute("src")).toBe(SCREEN_IMAGES.select_naruto_new);

    fireEvent.click(view.getByRole("button", { name: "GOKU" }));
    expect(image?.getAttribute("src")).toBe(SCREEN_IMAGES.select_goku_new);

    fireEvent.click(view.getByRole("button", { name: "LUFFY" }));
    expect(image?.getAttribute("src")).toBe(SCREEN_IMAGES.select_luffy);
  });
});
