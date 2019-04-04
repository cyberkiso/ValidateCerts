# input: file contains list of domain names
# output: two files - file contains valid domain names
#                     file contains invalid names
import sys
import getopt
import asyncio
import validators
import aiohttp
from aiohttp import ClientConnectorCertificateError
import os


Sem = asyncio.Semaphore(os.cpu_count() * 2)


def main(argv):
    global Sem
    try:
        opts, args = getopt.getopt(sys.argv[2:], "n:")
        for opt, arg in opts:
            if opt == '-n':
                Sem = asyncio.Semaphore(int(arg))
        inputfile: str = sys.argv[1]
        file = open(inputfile, "r")
        rawdata = file.readlines()
        file.close()
    except getopt.GetoptError:
        print("Usage: ValidateCerts.py <inputfile> [-n <requests_limit>]")
        sys.exit(2)
    except IOError as error:
        print("Error:", error)
    except IndexError:
        print("Error: input file name is missing."
              "Usage: ValidateCerts.py <inputfile>")
    domains = set()
    for domain in set(map(str.strip, rawdata)):
        if validators.domain(domain):
            domains.add(domain)
    print("Domains:", domains)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(validate_certs(domains))
    loop.close()


async def validate(domain):
    from _ssl import SSLCertVerificationError
    async with Sem:
        try:
            print(domain)
            url = "https://" + domain + "/"
            async with aiohttp.ClientSession() as session:
                await session.get(url)
                await session.close()
            Sem.release()
            return domain
        except ClientConnectorCertificateError as e:
            await session.close()
            Sem.release()
            if type(e.certificate_error is SSLCertVerificationError):
                return None
            print("Validate error: domain=%s  exception=%s", domain, e)
            return Exception("Validate error: domain=%s  exception=%s", domain, e)
        except Exception as e:
            print("Validate error: domain=%s  exception=%s", domain, e)
            return Exception("Validate error: domain=%s  exception=%s", domain, e)


async def validate_certs(domains, ):
    try:
        tasks = [asyncio.ensure_future(
            validate(domain)) for domain in domains]
        done = await asyncio.gather(*tasks)
        unvaliddomains = set()
        for result in done:
            tmp = type(result)
            if result is None:
                print("Unvalid: ", result)
                unvaliddomains.add(result+"\n")
                domains.remove(result)
            elif type(result) is Exception:
                domains.remove(result)
        for domain in domains:
            print("Valid: ", domain)
        validfile = open("Valid", "w")
        validfile.writelines(domains)
        validfile.close()
        unvalidfile = open("Unvalid", "w")
        unvalidfile.writelines(unvaliddomains)
        unvalidfile.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main(sys.argv[1:])
