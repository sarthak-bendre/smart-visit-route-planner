"""Smart Visit Route Planner: priority scoring, distance matrix, route optimisation, reporting."""

# Every route starts and ends at the branch office.
BRANCH_OFFICE = {
    "name": "Branch Office (Shivajinagar)",
    "latitude": 18.5308,
    "longitude": 73.8475,
}

REQUIRED_COLUMNS = [
    "dealer_id",
    "dealer_name",
    "area",
    "latitude",
    "longitude",
    "monthly_target_lakh",
    "achieved_lakh",
    "pending_issues",
    "days_since_last_visit",
]
