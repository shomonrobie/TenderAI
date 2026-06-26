# utils/currency_transformer.py
# pip install num2words
import math
import re
import num2words


def number_to_bangladesh_taka_words(amount):
    """
    Convert a number to Bangladeshi Taka words with proper paisa handling.
    Example: 51705.44 -> "Fifty One Thousand Seven Hundred Five Taka and Forty Four Paisa Only"
    """
    if amount is None or amount == 0:
        return "Zero Taka Only"
    
    # Split into taka and paisa
    taka = int(amount)
    paisa = int(round((amount - taka) * 100))
    
    # Handle negative numbers
    is_negative = taka < 0
    taka = abs(taka)
    
    # Convert taka part
    taka_words = _number_to_words(taka)
    
    # Build the result
    result = []
    
    if is_negative:
        result.append("Minus")
    
    if taka > 0:
        result.append(f"{taka_words} Taka")
    
    if paisa > 0:
        paisa_words = _number_to_words(paisa)
        result.append(f"and {paisa_words} Paisa")
    
    result.append("Only")
    
    return " ".join(result)


def _number_to_words(num):
    """Convert a number to words (1-999,999)"""
    if num == 0:
        return "Zero"
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    if num < 20:
        return ones[num]
    
    if num < 100:
        return tens[num // 10] + ("" if num % 10 == 0 else " " + ones[num % 10])
    
    if num < 1000:
        return ones[num // 100] + " Hundred" + ("" if num % 100 == 0 else " " + _number_to_words(num % 100))
    
    if num < 100000:
        return _number_to_words(num // 1000) + " Thousand" + ("" if num % 1000 == 0 else " " + _number_to_words(num % 1000))
    
    if num < 10000000:
        return _number_to_words(num // 100000) + " Lakh" + ("" if num % 100000 == 0 else " " + _number_to_words(num % 100000))
    
    return _number_to_words(num // 10000000) + " Crore" + ("" if num % 10000000 == 0 else " " + _number_to_words(num % 10000000))


# Alternative simpler version using built-in libraries
def number_to_bangladesh_taka_words_simple(amount):
    """
    Simpler version using num2words if available.
    Requires: pip install num2words
    """
    try:
        from num2words import num2words
        
        taka = int(amount)
        paisa = int(round((amount - taka) * 100))
        
        taka_words = num2words(taka, lang='en').title()
        
        if paisa > 0:
            paisa_words = num2words(paisa, lang='en').title()
            return f"{taka_words} Taka and {paisa_words} Paisa Only"
        else:
            return f"{taka_words} Taka Only"
    except ImportError:
        # Fallback to manual function
        return number_to_bangladesh_taka_words(amount)