import { projects } from "./projects-data";

export const MIRROR_ORIGIN = "https://parthh.in";

const serializedProjects = JSON.stringify(projects);

export const DOM_PATCH_SCRIPT = String.raw`(() => {
  const stateKey = "__nithinPortfolioPatch";
  if (window[stateKey]) {
    return;
  }
  window[stateKey] = true;

  const PROJECTS = ${serializedProjects};

  const KNOWN_TECH = new Set([
    "React",
    "TypeScript",
    "Next.js",
    "Tailwind CSS",
    "Rune's AI",
    "Framer Motion",
    "Node.js",
    "Vercel",
    "Prism.js",
    "LangGraph",
    "Tavily",
    "Appwrite",
    "GSAP",
    "Python",
    "LLM",
    "CNN",
    "OpenCV",
    "MongoDB",
    "Web3",
    "Google Maps API",
    "Firebase"
  ]);

  const OLD_TITLES = new Set(["Rune", "RuneHub", "RuneLearn", "RuneAI", "Old Portfolio"]);
  const ALL_TITLES = new Set([...OLD_TITLES, ...PROJECTS.map((project) => project.title)]);

  const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();

  const setText = (node, text) => {
    if (!node) {
      return;
    }
    if (normalize(node.textContent) !== text) {
      node.textContent = text;
    }
  };

  const patchHero = () => {
    const hero = Array.from(document.querySelectorAll("h1")).find((heading) => normalize(heading.textContent) === "Parth");
    setText(hero, "Nithin R");
  };

  const patchShowcaseLabel = () => {
    const nodes = Array.from(document.querySelectorAll("h1, h2, h3, span, p, div"));
    nodes.forEach((node) => {
      const text = normalize(node.textContent);
      if (text === "VENTURE") {
        setText(node, "PROJECT");
      }
      if (text === "VENTURE SHOWCASE") {
        setText(node, "PROJECT SHOWCASE");
      }
    });
  };

  const applyProjectText = (card, data) => {
    const titles = Array.from(card.querySelectorAll("h3")).filter((title) => ALL_TITLES.has(normalize(title.textContent)));
    titles.forEach((title) => setText(title, data.title));

    const descriptionParagraphs = Array.from(card.querySelectorAll("p")).filter((paragraph) => {
      const text = normalize(paragraph.textContent);
      return text.length > 80;
    });
    descriptionParagraphs.forEach((paragraph) => setText(paragraph, data.description[0]));

    const bulletLists = Array.from(card.querySelectorAll("ul")).filter((list) => {
      const items = Array.from(list.querySelectorAll("li"));
      if (items.length < 2) {
        return false;
      }
      const meaningfulItems = items.filter((item) => normalize(item.textContent).length > 20);
      return meaningfulItems.length >= 2;
    });

    bulletLists.forEach((list) => {
      const items = Array.from(list.querySelectorAll("li"));
      const meaningfulItems = items.filter((item) => normalize(item.textContent).length > 20);
      if (meaningfulItems[0]) {
        meaningfulItems[0].textContent = data.description[0];
      }
      if (meaningfulItems[1]) {
        meaningfulItems[1].textContent = data.description[1];
      }
      for (let index = meaningfulItems.length - 1; index >= 2; index -= 1) {
        meaningfulItems[index].remove();
      }
    });
  };

  const updateBadgeText = (badge, text) => {
    const icon = badge.querySelector("img");
    if (icon) {
      badge.innerHTML = "";
      badge.append(icon);
      badge.append(document.createTextNode(text));
      return;
    }
    badge.textContent = text;
  };

  const getBadgeGroups = (card) => {
    const containers = Array.from(card.querySelectorAll("div"));
    const candidateGroups = containers.filter((container) => {
      const badges = Array.from(container.querySelectorAll("img")).map((icon) => icon.parentElement).filter(Boolean);
      const validBadges = badges.filter((badge) => KNOWN_TECH.has(normalize(badge.textContent)));
      return validBadges.length >= 3;
    });

    return candidateGroups.filter((group) => {
      const nested = candidateGroups.some((other) => other !== group && group.contains(other));
      return !nested;
    });
  };

  const applyTechStack = (card, tech) => {
    const groups = getBadgeGroups(card);
    groups.forEach((group) => {
      const badges = Array.from(group.querySelectorAll("img"))
        .map((icon) => icon.parentElement)
        .filter((badge) => Boolean(badge) && KNOWN_TECH.has(normalize(badge.textContent)));

      badges.forEach((badge, index) => {
        if (index < tech.length) {
          badge.style.display = "";
          updateBadgeText(badge, tech[index]);
          return;
        }
        badge.style.display = "none";
      });
    });
  };

  const applyProjectLink = (card, github) => {
    const links = Array.from(card.querySelectorAll("a"));
    links.forEach((link) => {
      if (
        link.classList.contains("project-frame") ||
        /rune\.codes|parthsharma\.me/.test(link.href)
      ) {
        link.href = github;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.style.cursor = "pointer";
      }
    });

    card.dataset.githubUrl = github;
    card.style.cursor = "pointer";

    if (card.dataset.githubClickable === "1") {
      return;
    }

    card.addEventListener(
      "click",
      (event) => {
        if (event.defaultPrevented) {
          return;
        }
        if (event.target instanceof HTMLElement && event.target.closest("a")) {
          return;
        }
        const destination = card.dataset.githubUrl;
        if (!destination) {
          return;
        }
        window.open(destination, "_blank", "noopener,noreferrer");
      },
      false
    );

    card.dataset.githubClickable = "1";
  };

  const patchProjects = () => {
    const cards = Array.from(document.querySelectorAll(".project-card"));
    if (!cards.length) {
      return;
    }

    cards.forEach((card, index) => {
      const data = PROJECTS[index];
      if (!data) {
        card.remove();
        return;
      }

      card.style.display = "";
      applyProjectText(card, data);
      applyTechStack(card, data.tech);
      applyProjectLink(card, data.github);
    });
  };

  const runPatch = () => {
    patchHero();
    patchShowcaseLabel();
    patchProjects();
  };

  let raf = 0;
  const schedulePatch = () => {
    if (raf) {
      return;
    }
    raf = window.requestAnimationFrame(() => {
      raf = 0;
      runPatch();
    });
  };

  runPatch();

  const observer = new MutationObserver(schedulePatch);
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.addEventListener("load", schedulePatch);
  window.addEventListener("popstate", schedulePatch);
  document.addEventListener("visibilitychange", schedulePatch);
  window.setInterval(runPatch, 1200);
})();`;

export function injectPatchScript(html: string) {
  const scriptTag = `<script>${DOM_PATCH_SCRIPT}</script>`;
  if (html.includes("</body>")) {
    return html.replace("</body>", `${scriptTag}</body>`);
  }
  return `${html}${scriptTag}`;
}
