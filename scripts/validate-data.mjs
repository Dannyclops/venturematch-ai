import { readFile } from "node:fs/promises";

const dataUrl = new URL("../data/", import.meta.url);

const fundingStages = new Set([
  "bootstrapped",
  "pre_seed",
  "seed",
  "series_a",
  "series_b",
  "series_c_plus",
  "growth",
]);

const industries = new Set([
  "agritech",
  "climate_tech",
  "consumer",
  "cybersecurity",
  "e_commerce",
  "edtech",
  "enterprise_software",
  "fintech",
  "healthtech",
  "logistics_mobility",
]);

const businessModels = new Set([
  "b2b",
  "b2c",
  "b2b2c",
  "d2c",
  "marketplace",
  "saas",
  "other",
]);

const investorTypes = new Set([
  "angel",
  "corporate_vc",
  "family_office",
  "micro_vc",
  "venture_capital",
]);

const investmentRoles = new Set(["lead", "follow", "flexible"]);
const stageFlexibilities = new Set(["strict", "adjacent", "open"]);
const supportedCurrencies = new Set(["USD", "EUR", "TRY", "NGN", "GHS", "KES", "ZAR", "EGP", "AED"]);
const fundingStageOrder = new Map([
  ["bootstrapped", 0],
  ["pre_seed", 1],
  ["seed", 2],
  ["series_a", 3],
  ["series_b", 4],
  ["series_c_plus", 5],
  ["growth", 6],
]);
const countryCodeNames = new Map([
  ["AE", "united arab emirates"],
  ["EG", "egypt"],
  ["GH", "ghana"],
  ["KE", "kenya"],
  ["NG", "nigeria"],
  ["TR", "turkiye"],
  ["ZA", "south africa"],
]);
const geographyAliases = new Map([
  ["middle east and north africa", "mena"],
  ["turkey", "turkiye"],
  ["u a e", "united arab emirates"],
  ["uae", "united arab emirates"],
]);
const countryRegions = new Map([
  ["botswana", ["africa", "southern africa", "emerging markets"]],
  ["cote d'ivoire", ["africa", "west africa", "emerging markets"]],
  ["egypt", ["africa", "mena", "emerging markets"]],
  ["ghana", ["africa", "west africa", "emerging markets"]],
  ["jordan", ["mena", "emerging markets"]],
  ["kenya", ["africa", "east africa", "emerging markets"]],
  ["namibia", ["africa", "southern africa", "emerging markets"]],
  ["nigeria", ["africa", "west africa", "emerging markets"]],
  ["saudi arabia", ["mena", "emerging markets"]],
  ["senegal", ["africa", "west africa", "emerging markets"]],
  ["south africa", ["africa", "southern africa", "emerging markets"]],
  ["tanzania", ["africa", "east africa", "emerging markets"]],
  ["turkiye", ["europe", "southeast europe", "emerging markets"]],
  ["uganda", ["africa", "east africa", "emerging markets"]],
  ["united arab emirates", ["mena", "emerging markets"]],
]);
const idPattern = /^[a-z0-9][a-z0-9_-]{2,63}$/;
const countryPattern = /^[A-Z]{2}$/;

const errors = [];

function fail(path, message) {
  errors.push(`${path}: ${message}`);
}

function expect(condition, path, message) {
  if (!condition) fail(path, message);
}

function expectString(value, path, minimum = 1, maximum = Number.POSITIVE_INFINITY) {
  expect(typeof value === "string", path, "must be a string");
  if (typeof value === "string") {
    expect(value.length >= minimum, path, `must contain at least ${minimum} characters`);
    expect(value.length <= maximum, path, `must contain at most ${maximum} characters`);
  }
}

function expectStringArray(value, path, minimum = 0, maximum = Number.POSITIVE_INFINITY) {
  expect(Array.isArray(value), path, "must be an array");
  if (!Array.isArray(value)) return;

  expect(value.length >= minimum, path, `must contain at least ${minimum} items`);
  expect(value.length <= maximum, path, `must contain at most ${maximum} items`);
  value.forEach((item, index) => expectString(item, `${path}[${index}]`));
  expect(new Set(value).size === value.length, path, "must not contain duplicates");
}

function expectEnum(value, allowed, path) {
  expect(allowed.has(value), path, `contains unsupported value '${value}'`);
}

function expectId(value, path) {
  expect(typeof value === "string" && idPattern.test(value), path, "must be a valid entity ID");
}

function expectLocation(value, path) {
  expect(value && typeof value === "object" && !Array.isArray(value), path, "must be an object");
  if (!value || typeof value !== "object" || Array.isArray(value)) return;
  expect(countryPattern.test(value.country_code ?? ""), `${path}.country_code`, "must be a two-letter uppercase code");
  if (value.city !== null && value.city !== undefined) expectString(value.city, `${path}.city`, 2, 100);
  if (value.region !== null && value.region !== undefined) expectString(value.region, `${path}.region`, 2, 100);
}

function expectMoneyAmount(value, path) {
  expect(value && typeof value === "object" && !Array.isArray(value), path, "must be an object");
  if (!value || typeof value !== "object" || Array.isArray(value)) return;
  expect(Number.isInteger(value.amount) && value.amount > 0, `${path}.amount`, "must be a positive integer");
  expectEnum(value.currency, supportedCurrencies, `${path}.currency`);
}

function expectMoneyRange(value, path) {
  expect(value && typeof value === "object" && !Array.isArray(value), path, "must be an object");
  if (!value || typeof value !== "object" || Array.isArray(value)) return;
  expect(Number.isInteger(value.minimum) && value.minimum >= 0, `${path}.minimum`, "must be a non-negative integer");
  expect(Number.isInteger(value.maximum) && value.maximum > 0, `${path}.maximum`, "must be a positive integer");
  expect(value.maximum >= value.minimum, path, "maximum must be greater than or equal to minimum");
  expectEnum(value.currency, supportedCurrencies, `${path}.currency`);
}

function expectUniqueIds(records, collectionName) {
  const ids = records.map((record) => record.id);
  expect(new Set(ids).size === ids.length, collectionName, "contains duplicate entity IDs");
}

function validateBusiness(business, index) {
  const path = `businesses[${index}]`;
  expectId(business.id, `${path}.id`);
  expectString(business.name, `${path}.name`, 2, 120);
  expectString(business.one_liner, `${path}.one_liner`, 10, 180);
  expectString(business.description, `${path}.description`, 40, 2000);
  expectEnum(business.primary_industry, industries, `${path}.primary_industry`);
  expectStringArray(business.industry_tags, `${path}.industry_tags`, 1, 8);
  expectLocation(business.headquarters, `${path}.headquarters`);
  expectStringArray(business.operating_markets, `${path}.operating_markets`, 1, 20);
  expectEnum(business.funding_stage, fundingStages, `${path}.funding_stage`);
  expectMoneyAmount(business.amount_raising, `${path}.amount_raising`);
  expectEnum(business.business_model, businessModels, `${path}.business_model`);
  expectStringArray(business.keywords, `${path}.keywords`, 1, 20);

  if (business.traction !== null && business.traction !== undefined) {
    const tractionPath = `${path}.traction`;
    expect(typeof business.traction.is_revenue_generating === "boolean", `${tractionPath}.is_revenue_generating`, "must be boolean");
    if (business.traction.annual_revenue) expectMoneyAmount(business.traction.annual_revenue, `${tractionPath}.annual_revenue`);
    if (business.traction.monthly_recurring_revenue) {
      expectMoneyAmount(business.traction.monthly_recurring_revenue, `${tractionPath}.monthly_recurring_revenue`);
    }
    if (!business.traction.is_revenue_generating) {
      expect(!business.traction.annual_revenue, tractionPath, "non-revenue business cannot report annual revenue");
      expect(!business.traction.monthly_recurring_revenue, tractionPath, "non-revenue business cannot report monthly revenue");
    }
  }
}

function validateInvestor(investor, index, portfolioIds) {
  const path = `investors[${index}]`;
  expectId(investor.id, `${path}.id`);
  expectString(investor.name, `${path}.name`, 2, 120);
  expectEnum(investor.investor_type, investorTypes, `${path}.investor_type`);
  expectString(investor.thesis, `${path}.thesis`, 40, 2000);
  expect(Array.isArray(investor.preferred_industries), `${path}.preferred_industries`, "must be an array");
  investor.preferred_industries?.forEach((value, itemIndex) =>
    expectEnum(value, industries, `${path}.preferred_industries[${itemIndex}]`),
  );
  expect(Array.isArray(investor.excluded_industries), `${path}.excluded_industries`, "must be an array");
  investor.excluded_industries?.forEach((value, itemIndex) =>
    expectEnum(value, industries, `${path}.excluded_industries[${itemIndex}]`),
  );
  const overlap = investor.preferred_industries?.filter((value) => investor.excluded_industries?.includes(value)) ?? [];
  expect(overlap.length === 0, path, "preferred and excluded industries overlap");
  expect(Array.isArray(investor.preferred_stages), `${path}.preferred_stages`, "must be an array");
  investor.preferred_stages?.forEach((value, itemIndex) =>
    expectEnum(value, fundingStages, `${path}.preferred_stages[${itemIndex}]`),
  );
  expect(Array.isArray(investor.exploratory_stages), `${path}.exploratory_stages`, "must be an array");
  investor.exploratory_stages?.forEach((value, itemIndex) =>
    expectEnum(value, fundingStages, `${path}.exploratory_stages[${itemIndex}]`),
  );
  expectEnum(investor.stage_flexibility, stageFlexibilities, `${path}.stage_flexibility`);
  const stageOverlap =
    investor.preferred_stages?.filter((value) => investor.exploratory_stages?.includes(value)) ?? [];
  expect(stageOverlap.length === 0, path, "preferred and exploratory stages overlap");
  if (investor.stage_flexibility === "strict") {
    expect(investor.exploratory_stages?.length === 0, path, "strict policy cannot define exploratory stages");
  }
  if (investor.stage_flexibility === "open") {
    expect(investor.exploratory_stages?.length === 0, path, "open policy must infer exploratory stages");
  }
  if (investor.stage_flexibility === "adjacent") {
    expect(investor.exploratory_stages?.length > 0, path, "adjacent policy requires exploratory stages");
    investor.exploratory_stages?.forEach((stage) => {
      const isAdjacent = investor.preferred_stages.some(
        (coreStage) => Math.abs(fundingStageOrder.get(stage) - fundingStageOrder.get(coreStage)) === 1,
      );
      expect(isAdjacent, path, `${stage} is not adjacent to a preferred stage`);
    });
  }
  expectMoneyRange(investor.ticket_size, `${path}.ticket_size`);
  expectStringArray(investor.preferred_geographies, `${path}.preferred_geographies`, 1, 20);
  expectEnum(investor.investment_role, investmentRoles, `${path}.investment_role`);
  expect(typeof investor.actively_investing === "boolean", `${path}.actively_investing`, "must be boolean");
  expect(typeof investor.requires_revenue === "boolean", `${path}.requires_revenue`, "must be boolean");
  expectStringArray(investor.portfolio_company_ids, `${path}.portfolio_company_ids`, 3, 5);
  investor.portfolio_company_ids?.forEach((portfolioId, itemIndex) => {
    expectId(portfolioId, `${path}.portfolio_company_ids[${itemIndex}]`);
    expect(portfolioIds.has(portfolioId), `${path}.portfolio_company_ids[${itemIndex}]`, "references a missing portfolio company");
  });
  expectStringArray(investor.keywords, `${path}.keywords`, 1, 20);
}

function validatePortfolioCompany(company, index) {
  const path = `portfolios[${index}]`;
  expectId(company.id, `${path}.id`);
  expectString(company.name, `${path}.name`, 2, 120);
  expectString(company.one_liner, `${path}.one_liner`, 10, 180);
  expectEnum(company.primary_industry, industries, `${path}.primary_industry`);
  expectLocation(company.headquarters, `${path}.headquarters`);
  expectEnum(company.funding_stage_at_investment, fundingStages, `${path}.funding_stage_at_investment`);
  expectEnum(company.business_model, businessModels, `${path}.business_model`);
  expectStringArray(company.keywords, `${path}.keywords`, 1, 20);
}

function validateFxSnapshot(snapshot) {
  expect(snapshot.base_currency === "USD", "fx.base_currency", "demo base currency must be USD");
  expect(snapshot.is_live === false, "fx.is_live", "demo rates must never be marked live");
  expectString(snapshot.source, "fx.source", 3, 120);
  expectString(snapshot.notice, "fx.notice", 10, 500);
  expect(Array.isArray(snapshot.rates), "fx.rates", "must be an array");

  const rateCurrencies = snapshot.rates?.map((item) => item.currency) ?? [];
  expect(new Set(rateCurrencies).size === rateCurrencies.length, "fx.rates", "contains duplicate currencies");
  supportedCurrencies.forEach((currency) => {
    expect(rateCurrencies.includes(currency), "fx.rates", `is missing ${currency}`);
  });
  snapshot.rates?.forEach((item, index) => {
    expectEnum(item.currency, supportedCurrencies, `fx.rates[${index}].currency`);
    expect(Number(item.rate_to_base) > 0, `fx.rates[${index}].rate_to_base`, "must be positive");
  });
  const baseRate = snapshot.rates?.find((item) => item.currency === snapshot.base_currency);
  expect(Number(baseRate?.rate_to_base) === 1, "fx.rates", "must include USD with rate 1");
}

function rateMap(snapshot) {
  return new Map(snapshot.rates.map((item) => [item.currency, Number(item.rate_to_base)]));
}

function stageIsAcceptedForDiscovery(stage, investor) {
  if (investor.preferred_stages.includes(stage)) return true;
  if (investor.stage_flexibility === "open") return true;
  return investor.exploratory_stages.includes(stage);
}

function normalizeGeography(value) {
  const normalized = value
    .toLocaleLowerCase("en-US")
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/’/g, "'")
    .replace(/\./g, " ")
    .replace(/-/g, " ")
    .trim()
    .replace(/\s+/g, " ");
  return geographyAliases.get(normalized) ?? normalized;
}

function businessGeographyTags(business) {
  const directValues = [
    ...business.operating_markets,
    business.headquarters.city,
    business.headquarters.region,
    countryCodeNames.get(business.headquarters.country_code),
  ].filter(Boolean);
  const tags = new Set(directValues.map(normalizeGeography));
  [...tags].forEach((value) => {
    for (const region of countryRegions.get(value) ?? []) tags.add(region);
  });
  return tags;
}

function geographyMatches(business, investor) {
  const investorGeographies = investor.preferred_geographies.map(normalizeGeography);
  if (investorGeographies.includes("global")) return true;
  const businessTags = businessGeographyTags(business);
  return investorGeographies.some((value) => businessTags.has(value));
}

function businessHasStructurallyEligibleInvestor(business, investors, rates) {
  const isRevenueGenerating = business.traction?.is_revenue_generating ?? false;
  const businessAmountInUsd = business.amount_raising.amount * rates.get(business.amount_raising.currency);
  return investors.some((investor) => {
    const industryMatches =
      investor.preferred_industries.includes(business.primary_industry) &&
      !investor.excluded_industries.includes(business.primary_industry);
    const stageMatches = stageIsAcceptedForDiscovery(business.funding_stage, investor);
    const investorMinimumInUsd = investor.ticket_size.minimum * rates.get(investor.ticket_size.currency);
    const investorMaximumInUsd = investor.ticket_size.maximum * rates.get(investor.ticket_size.currency);
    const amountMatches =
      businessAmountInUsd >= investorMinimumInUsd && businessAmountInUsd <= investorMaximumInUsd;
    const revenueMatches = !investor.requires_revenue || isRevenueGenerating;
    return (
      investor.actively_investing &&
      industryMatches &&
      stageMatches &&
      amountMatches &&
      geographyMatches(business, investor) &&
      revenueMatches
    );
  });
}

async function readJson(fileName) {
  const raw = await readFile(new URL(fileName, dataUrl), "utf8");
  return JSON.parse(raw);
}

const [manifest, fxSnapshot, businesses, investors, portfolios] = await Promise.all([
  readJson("manifest.json"),
  readJson("fx_rates.demo.json"),
  readJson("businesses.json"),
  readJson("investors.json"),
  readJson("portfolios.json"),
]);

expect(Array.isArray(businesses), "businesses", "must be a JSON array");
expect(Array.isArray(investors), "investors", "must be a JSON array");
expect(Array.isArray(portfolios), "portfolios", "must be a JSON array");

if (Array.isArray(businesses) && Array.isArray(investors) && Array.isArray(portfolios)) {
  validateFxSnapshot(fxSnapshot);
  const rates = rateMap(fxSnapshot);
  expect(businesses.length === manifest.counts.businesses, "manifest.counts.businesses", "does not match file count");
  expect(investors.length === manifest.counts.investors, "manifest.counts.investors", "does not match file count");
  expect(portfolios.length === manifest.counts.portfolio_companies, "manifest.counts.portfolio_companies", "does not match file count");

  expectUniqueIds(businesses, "businesses");
  expectUniqueIds(investors, "investors");
  expectUniqueIds(portfolios, "portfolios");

  const allEntityIds = [...businesses, ...investors, ...portfolios].map((record) => record.id);
  expect(new Set(allEntityIds).size === allEntityIds.length, "all entities", "IDs must be globally unique");

  businesses.forEach(validateBusiness);
  portfolios.forEach(validatePortfolioCompany);
  const portfolioIds = new Set(portfolios.map((company) => company.id));
  investors.forEach((investor, index) => validateInvestor(investor, index, portfolioIds));

  const referencedPortfolioIds = investors.flatMap((investor) => investor.portfolio_company_ids);
  expect(
    new Set(referencedPortfolioIds).size === referencedPortfolioIds.length,
    "investors.portfolio_company_ids",
    "a portfolio company must not belong to multiple demo investors",
  );
  portfolios.forEach((company) => {
    expect(referencedPortfolioIds.includes(company.id), company.id, "portfolio company is not linked to an investor");
  });

  industries.forEach((industry) => {
    expect(
      businesses.some((business) => business.primary_industry === industry),
      "businesses industry coverage",
      `has no '${industry}' business`,
    );
  });

  const structurallyMatchable = businesses.filter((business) =>
    businessHasStructurallyEligibleInvestor(business, investors, rates),
  );
  expect(
    structurallyMatchable.length >= 20,
    "businesses",
    "fewer than 20 businesses have an industry/stage/ticket/revenue-compatible investor",
  );
}

if (errors.length > 0) {
  console.error(`Synthetic dataset validation failed with ${errors.length} error(s):`);
  errors.forEach((error) => console.error(`- ${error}`));
  process.exitCode = 1;
} else {
  console.log("Synthetic dataset is valid.");
  console.log(`- Businesses: ${businesses.length}`);
  console.log(`- Investors: ${investors.length}`);
  console.log(`- Portfolio companies: ${portfolios.length}`);
  console.log(`- Industry coverage: ${new Set(businesses.map((item) => item.primary_industry)).size}/${industries.size}`);
  console.log(`- Currency coverage: ${new Set(businesses.map((item) => item.amount_raising.currency)).size}/${supportedCurrencies.size}`);
  console.log(
    `- Structurally discoverable businesses: ${businesses.filter((item) => businessHasStructurallyEligibleInvestor(item, investors, rateMap(fxSnapshot))).length}/${businesses.length}`,
  );
}

