# input: file contains list of domain names
# output: two files - file contains valid domain names
#                     file contains invalid names
import sys
import getopt
import asyncio
import validators
import aiohttp
import os
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
        with open(file_name, "r") as file:
            raw_data = file.readlines()
        domains = set(map(str.strip, raw_data))
        domains_unchecked = set()
        for domain in domains:
            if validators.domain(domain):
                domains_unchecked.add(domain)
        log.debug(f"Domains: {domains_unchecked}")
        loop = asyncio.get_event_loop()
        valid_domains = loop.run_until_complete(validate_certs(domains_unchecked, sem))
        loop.close()
        valid_domains = [x + "\n" for x in valid_domains]
        with open("Valid", "w") as valid_file:
            valid_file.writelines(valid_domains)
        unvalid_domains = set(raw_data)
        for domain in valid_domains:
            unvalid_domains.remove(domain)
        with open("Unvalid", "w") as unvalid_file:
            unvalid_file.writelines(unvalid_domains)
    except getopt.GetoptError:
        log.error("Usage: ValidateCerts.py -f <inputfile> [-n <requests_limit>]")
    except IndexError:
        log.error("Error: input file name is missing."
                  "Usage: ValidateCerts.py -f <inputfile>")
    except Exception as e:
        log.error(f"Exception: {e}")


async def validate(domain, sem):
    async with sem:
        try:
            log.debug(f"Validate domain={domain}")
            url = f"https://{domain}/"
            async with aiohttp.ClientSession() as session:
                await session.get(url)
            sem.release()
            return domain
        except Exception as e:
            log.debug(f"Validate error: domain={domain} exception={e}")
            return None
        finally:
            sem.release()


async def validate_certs(domains, sem):
    try:
        tasks = [asyncio.ensure_future(validate(domain, sem)) for domain in domains]
        done = await asyncio.gather(*tasks)
        valid_domains = set()
        for result in done:
            if result is not None:
                valid_domains.add(result)
        return valid_domains
    except Exception as e:
        log.error(f"Exception: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
