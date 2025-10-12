"""
SMTP-based email validation.
100% free - uses standard SMTP protocol to verify emails.
"""

import smtplib
import dns.resolver
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SMTPEmailValidator:
    """
    Verify email addresses using SMTP without sending messages.
    
    How it works:
    1. Extract domain from email
    2. Get MX (mail exchange) records via DNS
    3. Connect to mail server
    4. Use RCPT TO command to check if email exists
    5. Disconnect without sending anything
    
    This is completely free and uses standard protocols!
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.sender_email = 'verify@leadgen.local'  # Fake sender for verification
    
    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify if an email address exists.
        
        Args:
            email: Email address to verify
        
        Returns:
            {
                'email': 'john@acme.com',
                'valid': True,
                'deliverable': True,
                'method': 'smtp',
                'mx_records': True,
                'error': None
            }
        """
        result = {
            'email': email,
            'valid': False,
            'deliverable': False,
            'method': 'smtp',
            'mx_records': False,
            'error': None
        }
        
        try:
            # Step 1: Basic syntax validation
            if '@' not in email or '.' not in email.split('@')[1]:
                result['error'] = 'invalid_syntax'
                return result
            
            # Step 2: Extract domain
            domain = email.split('@')[1]
            
            # Step 3: Check MX records
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                if not mx_records:
                    result['error'] = 'no_mx_records'
                    return result
                
                result['mx_records'] = True
                # Get highest priority MX record (lowest number = highest priority)
                mx_host = str(sorted(mx_records, key=lambda x: x.preference)[0].exchange).rstrip('.')
                
            except dns.resolver.NXDOMAIN:
                result['error'] = 'domain_not_found'
                return result
            except dns.resolver.NoAnswer:
                result['error'] = 'no_mx_records'
                return result
            except Exception as e:
                result['error'] = f'dns_error: {str(e)}'
                return result
            
            # Step 4: Connect to mail server and verify
            try:
                with smtplib.SMTP(timeout=self.timeout) as server:
                    server.connect(mx_host)
                    server.helo(server.local_hostname)
                    server.mail(self.sender_email)
                    
                    # Step 5: Verify email with RCPT TO
                    code, message = server.rcpt(email)
                    
                    # Response codes:
                    # 250 = email exists ✅
                    # 550 = email doesn't exist ❌
                    # 451/452 = temporary error (assume valid)
                    # 421 = service not available
                    
                    if code == 250:
                        result['valid'] = True
                        result['deliverable'] = True
                    elif code in [451, 452]:
                        # Temporary error, assume valid
                        result['valid'] = True
                        result['deliverable'] = True
                        result['error'] = 'temp_error_assumed_valid'
                    else:
                        result['valid'] = False
                        result['deliverable'] = False
                        result['error'] = f'smtp_code_{code}'
                    
                    return result
            
            except smtplib.SMTPServerDisconnected:
                result['error'] = 'server_disconnected'
                # Assume valid if we can't verify (many servers block verification)
                result['valid'] = True
                result['deliverable'] = True
                return result
            
            except smtplib.SMTPConnectError:
                result['error'] = 'connection_failed'
                # Assume valid if we can't connect
                result['valid'] = True
                result['deliverable'] = True
                return result
            
            except Exception as e:
                result['error'] = f'smtp_error: {str(e)}'
                # Assume valid if verification fails (conservative approach)
                result['valid'] = True
                result['deliverable'] = True
                return result
        
        except Exception as e:
            result['error'] = f'validation_error: {str(e)}'
            return result
    
    def verify_multiple(self, emails: List[str]) -> List[Dict[str, Any]]:
        """
        Verify multiple emails efficiently.
        
        Args:
            emails: List of email addresses to verify
        
        Returns:
            List of verification results
        """
        results = []
        for email in emails:
            result = self.verify_email(email)
            results.append(result)
            logger.info(f"Verified {email}: valid={result['valid']}, deliverable={result['deliverable']}")
        
        return results
    
    def get_mx_records(self, domain: str) -> List[str]:
        """
        Get MX records for a domain.
        
        Args:
            domain: Domain to check (e.g., "acme.com")
        
        Returns:
            List of MX record hostnames
        """
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return [str(mx.exchange).rstrip('.') for mx in sorted(mx_records, key=lambda x: x.preference)]
        except Exception as e:
            logger.error(f"Error getting MX records for {domain}: {e}")
            return []
