# input: file contains list of domain names
# output: two files - file contains valid domain names
#                     file contains invalid names
import sys
import getopt
import asyncio
import validators
import aiohttp
import os
from aiohttp import ClientConnectorCertificateError
import logging


log = logging.getLogger('')
log.setLevel(logging.DEBUG)
format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(format)
log.addHandler(ch)


def main(argv):
    try:
        sem = asyncio.Semaphore(os.cpu_count() * 2)
        opts, args = getopt.getopt(sys.argv[1:], "f:n:")
        for opt, arg in opts:
            if opt == '-n':
                sem = asyncio.Semaphore(int(arg))
            if opt == '-f':
                if len(arg) > 0:
                    file_name = arg
                else:
                    raise getopt.GetoptError
        input_file = file_name
        with open(input_file, "r") as file:
            raw_data = file.readlines()
        domains = set()
        for domain in set(map(str.strip, raw_data)):
            if validators.domain(domain):
                domains.add(domain)
        log.debug(f"Domains: {domains}")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(validate_certs(domains, sem))
        loop.close()
    except getopt.GetoptError:
        log.error("Usage: ValidateCerts.py -f <inputfile> [-n <requests_limit>]")
    except IndexError:
        log.error("Error: input file name is missing."
                  "Usage: ValidateCerts.py -f <inputfile>")
    except Exception as e:
        log.error(f"Exception: {e}")


async def validate(domain, sem):
    from _ssl import SSLCertVerificationError
    async with sem:
        try:
            log.debug(f"Validate domain={domain}")
            url = f"https://{domain}/"
            async with aiohttp.ClientSession() as session:
                await session.get(url)
            sem.release()
            return domain
        except ClientConnectorCertificateError as e:
            sem.release()
            if type(e.certificate_error is SSLCertVerificationError):
                return None
            log.debug(f"Validate error: domain={domain} exception={e}")
            return \
                Exception(f"Validate error: domain={domain} exception={e}"), \
                domain
        except Exception as e:
            sem.release()
            log.debug(f"Validate error: domain={domain} exception={e}")
            return \
                Exception(f"Validate error: domain={domain} exception={e}"), \
                domain


async def validate_certs(domains, sem):
    try:
        tasks = [asyncio.ensure_future(validate(domain, sem)) for domain in domains]
        done = await asyncio.gather(*tasks)
        valid_domains = set()
        for result in done:
            if result is not None and type(result) is not tuple:
                valid_domains.add(result + "\n")
                domains.remove(result)
            elif type(result) is tuple:
                log.warning(f"Cannot get cert for domain={result[1]}")
                domains.remove(result[1])
        with open("Valid", "w") as valid_file:
            valid_file.writelines(valid_domains)
        with open("Unvalid", "w") as unvalid_file:
            unvalid_file.writelines(domains)
    except Exception as e:
        log.error(f"Exception: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
