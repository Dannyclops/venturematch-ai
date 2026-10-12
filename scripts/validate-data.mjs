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
const idPattern = /^[a-z0-9][a-z0-9_-]{2,63}$/;
const currencyPattern = /^[A-Z]{3}$/;
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
  expect(currencyPattern.test(value.currency ?? ""), `${path}.currency`, "must be a three-letter uppercase code");
}

function expectMoneyRange(value, path) {
  expect(value && typeof value === "object" && !Array.isArray(value), path, "must be an object");
  if (!value || typeof value !== "object" || Array.isArray(value)) return;
  expect(Number.isInteger(value.minimum) && value.minimum >= 0, `${path}.minimum`, "must be a non-negative integer");
  expect(Number.isInteger(value.maximum) && value.maximum > 0, `${path}.maximum`, "must be a positive integer");
  expect(value.maximum >= value.minimum, path, "maximum must be greater than or equal to minimum");
  expect(currencyPattern.test(value.currency ?? ""), `${path}.currency`, "must be a three-letter uppercase code");
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

function businessHasStructurallyEligibleInvestor(business, investors) {
  const isRevenueGenerating = business.traction?.is_revenue_generating ?? false;
  return investors.some((investor) => {
    const industryMatches = investor.preferred_industries.includes(business.primary_industry);
    const stageMatches = investor.preferred_stages.includes(business.funding_stage);
    const amountMatches =
      investor.ticket_size.currency === business.amount_raising.currency &&
      business.amount_raising.amount >= investor.ticket_size.minimum &&
      business.amount_raising.amount <= investor.ticket_size.maximum;
    const revenueMatches = !investor.requires_revenue || isRevenueGenerating;
    return industryMatches && stageMatches && amountMatches && revenueMatches;
  });
}

async function readJson(fileName) {
  const raw = await readFile(new URL(fileName, dataUrl), "utf8");
  return JSON.parse(raw);
}

const [manifest, businesses, investors, portfolios] = await Promise.all([
  readJson("manifest.json"),
  readJson("businesses.json"),
  readJson("investors.json"),
  readJson("portfolios.json"),
]);

expect(Array.isArray(businesses), "businesses", "must be a JSON array");
expect(Array.isArray(investors), "investors", "must be a JSON array");
expect(Array.isArray(portfolios), "portfolios", "must be a JSON array");

if (Array.isArray(businesses) && Array.isArray(investors) && Array.isArray(portfolios)) {
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
    businessHasStructurallyEligibleInvestor(business, investors),
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
  console.log(
    `- Structurally matchable businesses: ${businesses.filter((item) => businessHasStructurallyEligibleInvestor(item, investors)).length}/${businesses.length}`,
  );
}

