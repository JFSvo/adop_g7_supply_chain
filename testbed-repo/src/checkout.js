// Synthetic module for the ADOP testbed. Computes a cart total and creates
// a payment intent against the (fake) payments gateway client.

import { paymentsClient } from './payments-client.js';

const DB_CONNECTION = process.env.CHECKOUT_DB_URL ?? 'postgres://orders-db/orders';

export function computeTotal(cart) {
  const subtotal = cart.items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const tax = subtotal * cart.taxRate;
  return Math.round((subtotal + tax) * 100) / 100;
}

export async function createPaymentIntent(cart) {
  const amount = computeTotal(cart);
  return paymentsClient.createIntent({
    amount,
    currency: cart.currency ?? 'USD'
  });
}

// TODO(issue #142): checkout currently shares DB_CONNECTION with the
// fulfillment service. Split into its own database once provisioned.

// Patch outline for issue #142:
// - Define a separate database connection string in env vars for this module
// - Update import statements to use that new connection string
// - Ensure no data is shared between checkout and fulfillment services
// - Add code to initialize the dedicated database