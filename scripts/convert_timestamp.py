import datetime

# Unix timestamp from the JWT
EXP_TIMESTAMP = 1762975238

# Convert to datetime object
datetime_object = datetime.datetime.fromtimestamp(EXP_TIMESTAMP)

print(f"JWT Expiration Date (UTC): {datetime_object}")
