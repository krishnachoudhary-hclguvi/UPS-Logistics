# UPS-Logistics

Booking-time fraud detection for account-billed shipments.

The problem: packages booked on a legitimate shipper’s account are usually caught only after delivery, once the real shipper disputes the charge. The carrier then reverses the invoice and keeps the cost of a package that already moved.

The approach: a synchronous risk check on the ship confirm step, before a tracking number or label is issued. Start with rules and the billed account’s own history, in shadow mode, on account-billed shipments only.

See [docs/booking-fraud-approach.md](docs/booking-fraud-approach.md).
