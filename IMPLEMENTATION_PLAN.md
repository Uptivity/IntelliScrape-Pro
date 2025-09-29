# JustSell vs WSMarketplace CSV Format Implementation Plan

## Overview
Convert the current "Standard/Wholesale" mode system to "JustSell/WSMarketplace" with two distinct CSV output formats.

## Current State
- Standard Mode → WSMarketplace format
- Wholesale Mode → Same format with different settings
- Single CSV output structure

## Target State
- JustSell Mode → JustSell CSV format (Shopify-compatible)
- WSMarketplace Mode → Current CSV format
- Two completely different CSV output structures

## Changes Required

### 1. UI Changes
- [ ] Replace "Standard/Wholesale" dropdown with "JustSell/WSMarketplace"
- [ ] Update labels and descriptions
- [ ] Maintain existing functionality

### 2. Backend Changes
- [ ] Rename prompts:
  - `STRICT_PROMPT` → `WSMARKETPLACE_STRICT_PROMPT`
  - `WHOLESALER_STRICT_PROMPT` → `JUSTSELL_STRICT_PROMPT`
- [ ] Create two CSV generation functions
- [ ] Create field mapping dictionaries for each format

### 3. CSV Format Definitions

#### WSMarketplace Format (current)
```
Name, SKU, Category, Brand, RFQ, Description, Wholesale Price, MSRP,
Stock Count, Min Order, Expiry date, Key Features, Certificates,
Specifications, Images, Variations, Variants, Tiered Pricing, Status
```

#### JustSell Format (new - based on ov-shopify-converted.csv)
```
Product Slug, Product ID, Image, Name, Available in stock, Status,
Category ID, Category, Sub Category ID, Sub Category, Third Level Category ID,
Third Level Category, Filters, Brand Make, Model Version, RRP, Sale Price,
Cost per unit, Max Order Limit, Min Order Limit, Accounting System ID,
Is Featured, Continue selling when out of stock, Out of Stock Delivery Lead time,
MPN/Barcode/QR Code Ref, Country of Origin, Ingredients, Allergens, Nutrition,
Storage, Supplier, Product Type, Weight, Length, Height, Width, View,
Long Description, Short Description, Sort Order, Title, Body (HTML), Vendor,
Published, Image Src, Handle, Variant Grams, Variant Inventory Qty,
Variant Price, Variant Requires Shipping, Variant Taxable, Variant Barcode,
Cost per item, Option1 Value, Variant SKU, Focus Keyphrase, SEO Title,
Meta Description, Meta URL, Display Model, Available For Euronics
```

### 4. Field Mapping

#### Common Fields
- Name → Name (both formats)
- Brand → Brand Make (JustSell) / Brand (WSMarketplace)
- Category → Category (both, but JustSell has sub-levels)
- Description → Long Description (JustSell) / Description (WSMarketplace)

#### SKU Mapping
- WSMarketplace: `SKU` column
- JustSell: `Variant SKU` column

#### Price Mapping
- WSMarketplace: `Wholesale Price`, `MSRP`
- JustSell: `Cost per unit`, `RRP`, `Sale Price`

#### Stock Mapping
- WSMarketplace: `Stock Count`
- JustSell: `Variant Inventory Qty`, `Available in stock`

### 5. Implementation Steps
1. Update UI (frontend)
2. Create new field mapping constants
3. Create separate CSV generation functions
4. Update prompt selection logic
5. Test with both formats
6. Update documentation

## Technical Considerations
- Maintain backward compatibility during transition
- Handle missing fields gracefully
- Ensure SKU generation works for both formats
- Test with existing scraped data

## Testing Plan
- Test URL extraction with both modes
- Test product scraping with both modes
- Verify CSV output format correctness
- Test SKU generation for both formats
- Test with provided websites:
  - https://ovdistribution.co.uk/
  - https://habitcbd.com/
  - https://www.argos.co.uk/