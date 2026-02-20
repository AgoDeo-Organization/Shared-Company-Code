import os
import json
import requests
import datetime

from julien_python_toolkit import file_utilities, log_utilities


PATH_TO_CACHE = file_utilities.join(file_utilities.path_to_this_file(__file__), 'exchange_rate_cache.json')


class ExchangeRateGetter:
    """Base interface for all exchange rate providers."""

    def get_exchange_rate(self, date, base_currency, target_currency):
        """Get the exchange rate from a base currency to a target currency.

        Args:
            date: The date to fetch the exchange rate for.
            base_currency: The source currency code.
            target_currency: The destination currency code.

        Returns:
            The exchange rate as a float.

        Raises:
            NotImplementedError: Always raised by the base class.
        """
        raise NotImplementedError("Subclasses must implement this method.")


# ------------------------------------------------------------------ #
# Simple Exchange Rate Getter (for testing)
# ------------------------------------------------------------------ #
class SimpleExchangeRateGetter(ExchangeRateGetter):
    """Simple exchange rate provider that always returns a fixed value."""
     
    def get_exchange_rate(self, date, base_currency, target_currency):
        """Return a constant exchange rate for testing.

        Args:
            date: The date to fetch the exchange rate for.
            base_currency: The source currency code.
            target_currency: The destination currency code.

        Returns:
            Always returns 1.0.
        """
        return 1.0


# ------------------------------------------------------------------ #
# Open Exchange Rate Getter with Caching
# ------------------------------------------------------------------ #

logger = log_utilities.Logger("OpenExchangeRateGetterWithCache", "open_exchange_rate_getter.log", stream_log_level = log_utilities.INFO, file_log_level = log_utilities.DEBUG)

class OpenExchangeRateGetterWithCache(ExchangeRateGetter):
    """Exchange rate provider that uses Open Exchange Rates with local caching."""

    # NOTE: Uses the ExchangeRateAPI website. Requires an API key.

    def __init__(self, api_key, path_to_cache = PATH_TO_CACHE):
        """Initialize the exchange rate getter and load cache data.

        Args:
            api_key: API key string used to call Open Exchange Rates.
            path_to_cache: Path to the JSON cache file.

        Raises:
            ValueError: If api_key is missing or empty.
        """

        clean_api_key = str(api_key).strip()
        if not clean_api_key:
            raise ValueError("API key is required.")

        self.api_key = clean_api_key

        self.path_to_cache = path_to_cache
        self.cache = self._load_cache()

    def _load_cache(self):
        """Load cached exchange rates from disk.

        Returns:
            A dictionary of cached exchange rates.
        """

        if os.path.exists(self.path_to_cache):

            with open(self.path_to_cache, 'r') as file:
                return json.load(file)
        
        return {}

    def _save_cache(self):
        """Persist the current exchange rate cache to disk."""

        with open(self.path_to_cache, 'w') as file:
            json.dump(self.cache, file, indent = 4)

    def _fetch_from_api_with_base_currency_and_not_unity(self, date_str, target_currency):
        """Fetch an exchange rate from USD to a non-USD target currency.

        Args:
            date_str: Date string in YYYY-MM-DD format.
            target_currency: Currency code to convert USD into.

        Returns:
            The exchange rate from USD to the target currency.

        Raises:
            Exception: If the API request or response processing fails.
        """

        try:

            url = f"https://openexchangerates.org/api/historical/{date_str}.json?app_id={self.api_key}&base=USD&symbols={target_currency}"

            logger.debug(f"Fetching exchange rate from API: {url}")

            response = requests.get(url)

            if response.status_code != 200:
                raise Exception(f"Error fetching exchange rate: {response.status_code} ({response.text})")
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise Exception(f"Error decoding JSON response: {e}")
            
            try:
                return data['rates'][target_currency]
            except KeyError:
                raise Exception(f"Exchange rate data not available for {target_currency} on {date_str}")
        
        except Exception as e:
            raise Exception(f"Error fetching exchange rate 'USD -> {target_currency}' on {date_str}: {e}")

    def _fetch_from_api_with_base_currency(self, date_str, target_currency):
        """Fetch an exchange rate from USD to a target currency.

        Args:
            date_str: Date string in YYYY-MM-DD format.
            target_currency: Currency code to convert USD into.

        Returns:
            The exchange rate from USD to the target currency.
        """

        if target_currency == "USD":
            logger.debug("Target currency is 'USD' so rate is 1.0, no need to fetch from API.")
            return 1.0
        else:
            return self._fetch_from_api_with_base_currency_and_not_unity(date_str, target_currency)

    def _fetch_from_api(self, date_str, base_currency, target_currency):
        """Fetch an exchange rate for any currency pair using USD as the bridge.

        Args:
            date_str: Date string in YYYY-MM-DD format.
            base_currency: Source currency code.
            target_currency: Destination currency code.

        Returns:
            The exchange rate from base currency to target currency.
        """

        # NOTE: We need to use this formula because the API does not allow for base currencies other than USD

        logger.debug(f"To create rate '{base_currency} -> {target_currency}', we need 'USD -> {target_currency}' / 'USD -> {base_currency}'.")

        # Fetching numerator

        numerator_rate = self._fetch_from_api_with_base_currency(date_str, target_currency)

        logger.debug(f"Rate fetched for 'USD -> {target_currency}' is '{numerator_rate}'")

        # Fetching denominator

        denominator_rate = self._fetch_from_api_with_base_currency(date_str, base_currency)

        logger.debug(f"Rate fetched for 'USD -> {base_currency}' is '{denominator_rate}'")

        # Calculating final rate

        final_rate = numerator_rate / denominator_rate

        logger.debug(f"Final rate is '{final_rate}'")

        return final_rate

    def get_exchange_rate(self, date, base_currency, target_currency):
        """Get an exchange rate for a date and currency pair.

        Args:
            date: A datetime.date or datetime.datetime instance.
            base_currency: Source currency code.
            target_currency: Destination currency code.

        Returns:
            The exchange rate as a float.

        Raises:
            ValueError: If date is not a date or datetime object.
        """

        if not isinstance(date, datetime.date) and not isinstance(date, datetime.datetime):
            raise ValueError (f"The 'date' {date} must be a datetime.date or datetime.datetime object, but got '{type(date)}' instead.")

        logger.debug(f"Getting exchange rate for {date}, {base_currency} -> {target_currency}")

        date_str = date.strftime('%Y-%m-%d')
        cache_key = f"{date_str}_{base_currency}_{target_currency}"
        
        if cache_key in self.cache:
            logger.debug(f"Found exchange rate in cache: {self.cache[cache_key]}")
            return self.cache[cache_key]
        
        logger.debug("Exchange rate not found in cache. Fetching from API.")

        exchange_rate = self._fetch_from_api(date_str, base_currency, target_currency)

        logger.debug(f"Exchange rate fetched: {exchange_rate}")

        if exchange_rate is not None:

            self.cache[cache_key] = exchange_rate
            self._save_cache()

            logger.debug("Cache saved.")
        
        return exchange_rate
