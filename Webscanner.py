import requests
from bs4 import BeautifulSoup
import urllib.parse
import colorama
import re
from concurrent.futures import ThreadPoolExecutor
import sys
from typing import List, Dict, Set


class WebSecurityScanner:
    def __init__(self, target_url: str, max_depth: int = 3):
        """
        Initialize the security scanner with a target URL and maximum crawl depth.

        Args:
            target_url: The base URL to scan
            max_depth: Maximum depth for crawling links (default: 3)
        """
        self.target_url = target_url
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.vulnerabilities: List[Dict] = []
        self.session = requests.Session()

        # Initialize colorama for cross-platform colored output
        colorama.init()

    def normalize_url(self, url: str) -> str:
        """Normalize the URL to prevent duplicate checks"""
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def crawl(self, url: str, depth: int = 0) -> None:
        """
        Crawl the website to discover pages and endpoints.

        Args:
            url: Current URL to crawl
            depth: Current depth in the crawl tree
        """
        if depth > self.max_depth or url in self.visited_urls:
            return

        # Mark the URL as visited and fetch the page content
        try:
            self.visited_urls.add(url)
            response = self.session.get(url, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all links in the page
            links = soup.find_all('a', href=True)
            for link in links:
                next_url = urllib.parse.urljoin(url, link['href'])
                if next_url.startswith(self.target_url):
                    self.crawl(next_url, depth + 1)

        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")


    # Check for sql injection vulnerabilities in  GET requests and POST parameters in POST requests
    def check_sql_injection(self, url: str) -> None:
        """Test for potential SQL injection vulnerabilities"""
        sql_payloads = ["'", "1' OR '1'='1", "' OR 1=1--", "' UNION SELECT NULL--"]

        # for loop to test each payload
        for payload in sql_payloads:
            try:
                # Test GET parameters
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)

                # Test each parameter
                for param in params:
                    test_url = url.replace(f"{param}={params[param][0]}", 
                                         f"{param}={payload}")
                    response = self.session.get(test_url)

                    # Look for SQL error messages
                    if any(error in response.text.lower() for error in 
                        ['sql', 'mysql', 'sqlite', 'postgresql', 'oracle']):
                        self.report_vulnerability({
                            'type': 'SQL Injection',
                            'url': url,
                            'parameter': param,
                            'payload': payload
                        })

            except Exception as e:
                print(f"Error testing SQL injection on {url}: {str(e)}")

    # Check for Cross-Site Scripting vulnerabilities in GET parameters
    def check_xss(self, url: str) -> None:
        """Test for potential Cross-Site Scripting vulnerabilities"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')"
        ]

        # for loop to test each payload
        for payload in xss_payloads:
            try:
                # Test GET parameters
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)

                # Test each parameter
                for param in params:
                    test_url = url.replace(f"{param}={params[param][0]}", 
                                         f"{param}={urllib.parse.quote(payload)}")
                    response = self.session.get(test_url)

                    # Look for XSS payloads in the response
                    if payload in response.text:
                        self.report_vulnerability({
                            'type': 'Cross-Site Scripting (XSS)',
                            'url': url,
                            'parameter': param,
                            'payload': payload
                        })

            except Exception as e:
                print(f"Error testing XSS on {url}: {str(e)}")

    def check_sensitive_info(self, url: str) -> None:
    """Check for exposed sensitive information"""
    sensitive_patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'api_key': r'api[_-]?key[_-]?([\'"|`])([a-zA-Z0-9]{32,45})\1'
    }

    # for loop to test each pattern
    try:
        response = self.session.get(url)

        # Look for sensitive information in the response
        for info_type, pattern in sensitive_patterns.items():
            matches = re.finditer(pattern, response.text)
            for match in matches:
                self.report_vulnerability({
                    'type': 'Sensitive Information Exposure',
                    'url': url,
                    'info_type': info_type,
                    'pattern': pattern
                })

    # Exception handling for potential errors
    except Exception as e:
        print(f"Error checking sensitive information on {url}: {str(e)}")






