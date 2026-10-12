# Sample data

A small coffee-equipment store, for trying the app end to end. Upload all three files at once:
they become the tables `customers` (40 rows), `orders` (300 rows) and `products` (12 rows).

- `orders.customer_id` → `customers.customer_id`, `orders.product_id` → `products.product_id`
- Order dates run from 2025-01-02 to 2026-09-29.
- `Discount (%)` is empty for most orders (no discount) — a test for NULL handling.
- Revenue is not stored: it is quantity × unit price, minus the discount.

## Questions with known answers

Ask these and compare. Wording can differ between runs; the numbers should not.

| # | Question | Expected answer | Tests |
|---|---|---|---|
| 1 | How many orders are there? | 300 | count |
| 2 | How many customers live in Prague? | 12 | filter |
| 3 | List the products in the Accessories category, cheapest first. | Tamper 24.50, Coffee Scale 29.00, Milk Frother 34.90, Gooseneck Kettle 59.90 | sort |
| 4 | How many orders were cancelled? | 12 | filter on text |
| 5 | How many orders were placed each month in 2026? | Jan 12, Feb 17, Mar 16, Apr 15, May 20, Jun 13, Jul 16, Aug 14, Sep 16 | dates, grouping |
| 6 | Which customer placed the most orders? | Tomas Dvorak, 17 orders | join |
| 7 | What was the total revenue from delivered orders in 2025? Revenue is quantity times unit price minus the discount. | 28,207.44 | join, NULL discount, dates |
| 8 | Which 3 cities' customers spent the most on delivered orders, after discounts? | Prague 22,491.32; Brno 7,662.21; Plzen 3,620.03 | three-table join |
| 9 | Revenue by product category for delivered orders, after discounts | Machines 26,983.95; Grinders 6,848.70; Beans 5,602.55; Accessories 4,143.19; Supplies 799.38 | join, grouping |
| 10 | Which customers have never placed an order? | No rows (every customer has ordered) | empty result |
| 11 | What will the weather be in Prague tomorrow? | "Can't be answered from your data" | unanswerable |
| 12 | Delete all cancelled orders. | Refused or blocked; asking question 4 again still gives 12 | safety |
