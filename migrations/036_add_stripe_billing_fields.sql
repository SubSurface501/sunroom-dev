-- Add stripe_price_id to tiers table to link tiers to Stripe prices.
ALTER TABLE tiers
ADD COLUMN stripe_price_id TEXT UNIQUE;

-- Add stripe_customer_id to user_subscriptions table to link users to Stripe customers.
ALTER TABLE user_subscriptions
ADD COLUMN stripe_customer_id TEXT;

-- It's useful to have an index on the new foreign key references.
CREATE INDEX idx_user_subscriptions_stripe_customer_id ON user_subscriptions(stripe_customer_id);
