// frontend/script.js

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? "http://localhost:8000"
  : ""; // Production (Render with or without custom domain) - no prefix needed

const form = document.getElementById("qa-form");
const btnText = document.getElementById("btn-text");
const btnSpinner = document.getElementById("btn-spinner");

const resultEmpty = document.getElementById("result-empty");
const resultContent = document.getElementById("result-content");
const errorBox = document.getElementById("error-box");

// score elements
const overallScoreEl = document.getElementById("overall-score");
const scoreQualityEl = document.getElementById("score-quality");
const scoreSeoEl = document.getElementById("score-seo");
const scoreEngagementEl = document.getElementById("score-engagement");
const scoreStructureEl = document.getElementById("score-structure");

// content checks
const issuesListEl = document.getElementById("issues-list");
const grammarSummaryEl = document.getElementById("grammar-summary");
const toneSummaryEl = document.getElementById("tone-summary");
const ctaStatusEl = document.getElementById("cta-status");

// hashtags
const tagsFinalEl = document.getElementById("tags-final");
const tagsTrendingEl = document.getElementById("tags-trending");

// optimized
const optimizedTitleEl = document.getElementById("optimized-title");
const optimizedContentEl = document.getElementById("optimized-content");

// CTAs
const ctaListEl = document.getElementById("cta-list");

function setLoading(isLoading) {
  if (isLoading) {
    btnText.textContent = "Analyzing...";
    btnSpinner.classList.remove("hidden");
  } else {
    btnText.textContent = "Run QA";
    btnSpinner.classList.add("hidden");
  }
}

function safeGet(obj, path, fallback = null) {
  try {
    return path.split(".").reduce((acc, key) => (acc ? acc[key] : undefined), obj) ?? fallback;
  } catch {
    return fallback;
  }
}

const MANDATORY_HASHTAGS = ["#snssquare", "#snsihub", "#snsdesignthinking", "#designthinkers"];

function getScoreClass(score) {
  if (score >= 90) return 'excellent';
  if (score >= 75) return 'good';
  if (score >= 60) return 'average';
  return 'poor';
}

function isMandatoryHashtag(tag) {
  const normalized = tag.toLowerCase().replace(/[^a-z0-9]/g, '');
  return MANDATORY_HASHTAGS.some(mandatory =>
    mandatory.toLowerCase().replace(/[^a-z0-9]/g, '') === normalized
  );
}

function renderChips(container, items, { trending = false } = {}) {
  container.innerHTML = "";
  if (!items || !items.length) {
    container.innerHTML = '<span class="muted">None</span>';
    return;
  }

  items.forEach((item) => {
    let label = item;
    let competitionClass = '';
    let isMandatory = false;

    if (typeof item === "object" && item !== null) {
      label = item.tag || JSON.stringify(item);
      isMandatory = isMandatoryHashtag(label);
      if (item.competition_level) {
        const level = item.competition_level.toLowerCase();
        competitionClass = ` competition-${level}`;
        label += ` · ${item.competition_level}`;
      }
    } else {
      isMandatory = isMandatoryHashtag(label);
    }

    const chip = document.createElement("span");
    let className = "chip";
    if (isMandatory) {
      className += " mandatory";
    } else if (trending) {
      className += " trending";
    }
    className += competitionClass;
    chip.className = className;
    chip.textContent = label;
    container.appendChild(chip);
  });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.classList.add("hidden");
  errorBox.textContent = "";

  const platform = document.getElementById("platform").value;
  const title = document.getElementById("title").value.trim();
  const content = document.getElementById("content").value.trim();
  const hashtagsRaw = document.getElementById("hashtags").value.trim();
  const geo = document.getElementById("geo").value.trim();
  const niche = document.getElementById("niche").value.trim();
  const targetAudience = document.getElementById("target_audience").value.trim();

  if (!content) {
    errorBox.textContent = "Please paste some content to analyze.";
    errorBox.classList.remove("hidden");
    return;
  }

  const hashtags =
    hashtagsRaw.length > 0
      ? hashtagsRaw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
      : [];

  const payload = {
    platform,
    title: title || null,
    content,
    hashtags,
    geo: geo || null,
    niche: niche || null,
    target_audience: targetAudience || null,
  };

  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Server error");
    }

    const data = await res.json();
    const result = data.raw_json || data; // in case response_model changed

    // Show result container
    resultEmpty.classList.add("hidden");
    resultContent.classList.remove("hidden");

    // Scores with dynamic coloring
    const overallScore = result.overall_score ?? 0;
    overallScoreEl.textContent = overallScore;
    overallScoreEl.className = 'score-big ' + getScoreClass(overallScore);

    // Apply background color to score section
    const scoreSection = document.querySelector('.score-section');
    if (scoreSection) {
      scoreSection.className = 'score-section ' + getScoreClass(overallScore);
    }

    const breakdown = result.scores_breakdown || {};
    scoreQualityEl.textContent = breakdown.quality_score ?? "–";
    scoreQualityEl.className = 'score-value ' + getScoreClass(breakdown.quality_score ?? 0);

    scoreSeoEl.textContent = breakdown.seo_score ?? "–";
    scoreSeoEl.className = 'score-value ' + getScoreClass(breakdown.seo_score ?? 0);

    scoreEngagementEl.textContent = breakdown.engagement_score ?? "–";
    scoreEngagementEl.className = 'score-value ' + getScoreClass(breakdown.engagement_score ?? 0);

    scoreStructureEl.textContent = breakdown.structure_score ?? "–";
    scoreStructureEl.className = 'score-value ' + getScoreClass(breakdown.structure_score ?? 0);

    // Animate score bar
    const scoreBarFill = document.getElementById("score-bar-fill");
    setTimeout(() => {
      scoreBarFill.style.width = `${Math.min(overallScore, 100)}%`;
    }, 100);

    // Issues
    const issues = result.issues_found || [];
    issuesListEl.innerHTML = "";
    if (!issues.length) {
      issuesListEl.innerHTML = '<li class="muted">No major issues found.</li>';
    } else {
      issues.forEach((issue) => {
        const li = document.createElement("li");
        if (typeof issue === 'object' && issue !== null) {
          li.textContent = issue.issue || issue.message || JSON.stringify(issue);
        } else {
          li.textContent = issue;
        }
        issuesListEl.appendChild(li);
      });
    }

    // Content checks
    const checks = result.content_checks || {};
    grammarSummaryEl.textContent = `Grammar: ${checks.grammar_summary || "N/A"}`;
    toneSummaryEl.textContent = `Tone: ${checks.tone_summary || "N/A"}`;
    ctaStatusEl.textContent = `CTA: ${checks.cta_status || "N/A"}`;

    // Hashtags
    const tags = result.hashtags || {};
    const finalPack = safeGet(result, "final_output.final_hashtag_pack", []);
    renderChips(tagsFinalEl, finalPack);
    renderChips(tagsTrendingEl, tags.trending || [], { trending: true });

    // Optimized content
    const finalOut = result.final_output || {};
    optimizedTitleEl.textContent = finalOut.optimized_title || "";
    optimizedContentEl.textContent = finalOut.optimized_content || "";

    // CTAs
    const improvements = result.improvements || {};
    const ctas = improvements.cta_variants || [];
    ctaListEl.innerHTML = "";
    if (!ctas.length) {
      ctaListEl.innerHTML = '<li class="muted">No CTA variants returned.</li>';
    } else {
      ctas.forEach((cta) => {
        const li = document.createElement("li");
        li.textContent = cta;
        ctaListEl.appendChild(li);
      });
    }
  } catch (err) {
    console.error(err);
    errorBox.textContent = err.message || "Something went wrong.";
    errorBox.classList.remove("hidden");
  } finally {
    setLoading(false);
  }
});
