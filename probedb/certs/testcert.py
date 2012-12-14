#   Copyright 2010-2012 Opera Software ASA 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

'''
Created on 8. aug. 2010

@author: Yngve
'''
import unittest

class Test(unittest.TestCase):
	"""Perform a few simple tests with some certificates"""

	import sys
	sys.argv = ['', 'build']
	import build_certhandler

	def testName(self):
		import certhandler
		
		test = certhandler.Certificate(
"""
MIIDuDCCAqCgAwIBAgIQDPCOXAgWpa1Cf/DrJxhZ0DANBgkqhkiG9w0BAQUFADBI
MQswCQYDVQQGEwJVUzEgMB4GA1UEChMXU2VjdXJlVHJ1c3QgQ29ycG9yYXRpb24x
FzAVBgNVBAMTDlNlY3VyZVRydXN0IENBMB4XDTA2MTEwNzE5MzExOFoXDTI5MTIz
MTE5NDA1NVowSDELMAkGA1UEBhMCVVMxIDAeBgNVBAoTF1NlY3VyZVRydXN0IENv
cnBvcmF0aW9uMRcwFQYDVQQDEw5TZWN1cmVUcnVzdCBDQTCCASIwDQYJKoZIhvcN
AQEBBQADggEPADCCAQoCggEBAKukgeWVzfX2FI7CT8rU4niVWJxB4Q2ZQCQXOZEz
Zum+4YOvYlyJ0fwkW2Gz4BERQRwdbvC4u/jep4G6pkjGnx29vo6pQT64lO0pGtSO
0gMdA+9tDWccV9cGrcrI9f4Or2YlSASWC12juhbDCE/RRvgUXPLIXgGZbf2IzIao
wW8xQmxSPmjL8xk037uHGFaAJsTQ3MBv396gwpEWoGQRS0S8Hvbn+mPeZqx2pHGj
7DaUaHp3pLHnDi+BeuK1cobvomuL8A/b01k/unK8RCSc43Oz969XL0Imnal0ugBS
8kvNU3xHCzaFDmapCJcWNFfBZveA4+1wVMeT4C4oFVmHursCAwEAAaOBnTCBmjAT
BgkrBgEEAYI3FAIEBh4EAEMAQTALBgNVHQ8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB
/zAdBgNVHQ4EFgQUQjK2FvoE/f5dS3rD/fdMQB1aQ68wNAYDVR0fBC0wKzApoCeg
JYYjaHR0cDovL2NybC5zZWN1cmV0cnVzdC5jb20vU1RDQS5jcmwwEAYJKwYBBAGC
NxUBBAMCAQAwDQYJKoZIhvcNAQEFBQADggEBADDtT0rhWDpSclu1pqNlGKa7UTt3
6Z3q059c4EVlew3KW+JwULKUBRSuSceNQQcSc5R+DCMh/bwQf2AQWnL1mA6s7Ll/
3XpvXdMc9P+IBWlCqQVxyLesJugutIxq/3HcuLHfmbx8IVQr5Fiiu1cprp6poxkm
D5kuCLDv/WnPmRoJjeOnnyvJNjR7JLN4TJUXpAYmHrZkUjZfYGfZnMUFdAvnZyPS
CPyI6a6Lf+Ew9Dd+/cYy2i2eRDAwbO4H3tI0/NL/QPZL9GZGBlSm8jIKYyYwa5vR
3ItHuuG51WLQoqD0ZwV4KWMabwTW+MZMo5qxN7SN5ShLHZ4swrhovO0C7jE=
"""									
									)
		
		test2 = certhandler.Certificate(
"""
MIIEXDCCA0SgAwIBAgIEOGO5ZjANBgkqhkiG9w0BAQUFADCBtDEUMBIGA1UEChML
RW50cnVzdC5uZXQxQDA+BgNVBAsUN3d3dy5lbnRydXN0Lm5ldC9DUFNfMjA0OCBp
bmNvcnAuIGJ5IHJlZi4gKGxpbWl0cyBsaWFiLikxJTAjBgNVBAsTHChjKSAxOTk5
IEVudHJ1c3QubmV0IExpbWl0ZWQxMzAxBgNVBAMTKkVudHJ1c3QubmV0IENlcnRp
ZmljYXRpb24gQXV0aG9yaXR5ICgyMDQ4KTAeFw05OTEyMjQxNzUwNTFaFw0xOTEy
MjQxODIwNTFaMIG0MRQwEgYDVQQKEwtFbnRydXN0Lm5ldDFAMD4GA1UECxQ3d3d3
LmVudHJ1c3QubmV0L0NQU18yMDQ4IGluY29ycC4gYnkgcmVmLiAobGltaXRzIGxp
YWIuKTElMCMGA1UECxMcKGMpIDE5OTkgRW50cnVzdC5uZXQgTGltaXRlZDEzMDEG
A1UEAxMqRW50cnVzdC5uZXQgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkgKDIwNDgp
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArU1LqRKGsuqjIAcVFmQq
K0vRvwtKTY7tgHalZ7d4QMBzQshowNtTK91euHaYNZOLGp18EzoOH1u3Hs/lJBQe
sYGpjX24zGtLA/ECDNyrpUAkAH90lKGdCCmziAv1h3edVc3kw37XamSrhRSGlVuX
MlBvPci6Zgzj/L24ScF2iUkZ/cCovYmjZy/Gn7xxGWC4LeksyZB2ZnuU4q941mVT
XTzWnLLPKQP5L6RQstRIzgUyVYr9smRMDuSYB3Xbf9+5CFVghTAp+XtIpGmG4zU/
HoZdenoVve8AjhUiVBcAkCaTvA5JaJG/+EfTnZVCwQ5N328mz8MYIWJmQ3DW1cAH
4QIDAQABo3QwcjARBglghkgBhvhCAQEEBAMCAAcwHwYDVR0jBBgwFoAUVeSB0RGA
vtiJuQijMfmhJAkWuXAwHQYDVR0OBBYEFFXkgdERgL7YibkIozH5oSQJFrlwMB0G
CSqGSIb2fQdBAAQQMA4bCFY1LjA6NC4wAwIEkDANBgkqhkiG9w0BAQUFAAOCAQEA
WUesIYSKF8mciVMeuoCFGsY8Tj6xnLZ8xpJdGGQC49MGCBFhfGPjK50xA3B20qMo
oPS7mmNz7W3lKtvtFKkrxjYR0CvrB4ul2p5cGZ1WEvVUKcgF7bISKo30Axv/55IQ
h7A6tcOdBTcSo8f0FbnVpDkWm1M6I5HxqIKiaohowXkCIryqptau37AUX7iH0N18
f3v/rxzP5tsHrV7bhZ3QKw0z2wTR5klAEyt2+z7pnIkPFc4YsIV4IU9rTw76NmfN
B/L/CNDi3tm/Kq+4h4YhPATKt5Rof8886ZjXOP/swNlQ8C5LWK5Gb9Auw2DaclVy
vUxFnmG6v4SBkgPR0ml8xQ==
"""
								)
		
		if not test.IsSelfSigned():
			raise
		
		if not test.IsSignedBy(test):
			raise

		if not test2.IsSelfSigned():
			raise
		
		if not test2.IsSignedBy(test2):
			raise

		if test2.IsSignedBy(test):
			raise

		if test.IsSignedBy(test2):
			raise
	
		if not test.IssuerNameDER() or test.IssuerNameDER() != test.SubjectNameDER():
			raise
		
		if test.IssuerNameLine() != "/C=US/O=SecureTrust Corporation/CN=SecureTrust CA":
			raise
		
		if test.SubjectNameLine() != "/C=US/O=SecureTrust Corporation/CN=SecureTrust CA":
			raise

		if not test2.IssuerNameDER() or test2.IssuerNameDER() != test2.SubjectNameDER():
			raise
		
		text = test2.IssuerNameLine()
		if text != """/O=Entrust.net/OU=www.entrust.net/CPS_2048 incorp. by ref. (limits liab.)/OU=(c) 1999 Entrust.net Limited/CN=Entrust.net Certification Authority (2048)""":
			raise
		
		if test2.SubjectNameLine() != """/O=Entrust.net/OU=www.entrust.net/CPS_2048 incorp. by ref. (limits liab.)/OU=(c) 1999 Entrust.net Limited/CN=Entrust.net Certification Authority (2048)""":
			raise

		if test.GetSerialNumber() != "0x0CF08E5C0816A5AD427FF0EB271859D0":
			raise
		
		if test2.GetSerialNumber() != 0x3863b966:
			raise
	
		test_entrust = test2
		test_digicert = certhandler.Certificate(
"""
MIIEwDCCA6igAwIBAgIEOGPLSjANBgkqhkiG9w0BAQUFADCBtDEUMBIGA1UEChML
RW50cnVzdC5uZXQxQDA+BgNVBAsUN3d3dy5lbnRydXN0Lm5ldC9DUFNfMjA0OCBp
bmNvcnAuIGJ5IHJlZi4gKGxpbWl0cyBsaWFiLikxJTAjBgNVBAsTHChjKSAxOTk5
IEVudHJ1c3QubmV0IExpbWl0ZWQxMzAxBgNVBAMTKkVudHJ1c3QubmV0IENlcnRp
ZmljYXRpb24gQXV0aG9yaXR5ICgyMDQ4KTAeFw0wODExMDcyMDM4NDFaFw0xNDA3
MDEwNDAwMDBaMGMxCzAJBgNVBAYTAlVTMRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMx
GTAXBgNVBAsTEHd3dy5kaWdpY2VydC5jb20xIjAgBgNVBAMTGURpZ2lDZXJ0IEds
b2JhbCBDQSAoMjA0OCkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDE
PLzMuupi5p5CI6+0shGuYo3ZodOPzBRyGe2Z9v3eXbtZwLDCr2qZUpVXCzX/4Yb6
r6LDwQVlJyB2LwpUJXzqK92VQVebDzvPR+gBBozFREj8By7zcoMwUZSeaTqDqYeQ
FNlexKJ4j8E+1BlhDhrn3BqVIEG+bxfauBxB7piw+tcdNT8WpwQoE109BXWaLoae
LLAXhyBYV+/h6lVguCxwIawpYwwQ/GC8+dUcN2TVtPseqyY5Roiky80wZ8AmeeXK
aPki1+XSsbtITJsLmFtCkuXS7Q5HMPrdJ1ZjaqUBx46v8E47G1UVRNU+TVce4ZHq
uKCPzjpjX5aJugg+/kS7AgMBAAGjggEoMIIBJDAOBgNVHQ8BAf8EBAMCAQYwEgYD
VR0TAQH/BAgwBgEB/wIBADAnBgNVHSUEIDAeBggrBgEFBQcDAQYIKwYBBQUHAwIG
CCsGAQUFBwMEMDMGCCsGAQUFBwEBBCcwJTAjBggrBgEFBQcwAYYXaHR0cDovL29j
c3AuZW50cnVzdC5uZXQwMgYDVR0fBCswKTAnoCWgI4YhaHR0cDovL2NybC5lbnRy
dXN0Lm5ldC8yMDQ4Y2EuY3JsMBEGA1UdIAQKMAgwBgYEVR0gADAdBgNVHQ4EFgQU
Q0lH589A0ZqokvKMisqYk8/JCA8wHwYDVR0jBBgwFoAUVeSB0RGAvtiJuQijMfmh
JAkWuXAwGQYJKoZIhvZ9B0EABAwwChsEVjcuMQMCAIEwDQYJKoZIhvcNAQEFBQAD
ggEBAGgUlCIvPADB6IfhYPg91XNYOvbL3dNQt4AOHJu6M5wmLH4eJlpK4G0Ch6DD
Woy9gOtIx54iyu2amOO90ACoBXMizEGGmR1Z2C5UeiTedov3g3fJIOqH7O/rd41L
GaYm4AzKRwsNZXoOTukUSQA7vdSTI4sdZQ6gmElqJ/ZgalGAy5ZJSWSLSeXcB5+Z
CeVoGPLjq2rh62N6JS3J/j8Jn/gBDNVzbBa5BBySBTT/Ow+hDgGJV8sD35z/aF8Z
W5VX4pNfSbzSPS8U26jGpmEqrqHAdgTgK8OVHVa40o7K4K6/E7CRO+v/6Ts2pP2N
BihOJhXLn+HbRoukESiGrQOxT3U=
"""										)
		
		test_bugs = certhandler.Certificate(
"""										
MIIG6jCCBdKgAwIBAgIQBrRGenfGTY6Sw46A6Iw1FDANBgkqhkiG9w0BAQUFADBj
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSIwIAYDVQQDExlEaWdpQ2VydCBHbG9iYWwgQ0EgKDIw
NDgpMB4XDTA4MTEyMTAwMDAwMFoXDTEyMDEyNDIzNTk1OVowdDELMAkGA1UEBhMC
Tk8xDTALBgNVBAgTBE9zbG8xDTALBgNVBAcTBE9zbG8xGzAZBgNVBAoTEk9wZXJh
IFNvZnR3YXJlIEFTQTERMA8GA1UECxMIT3BlcmEgQ0ExFzAVBgNVBAMTDmJ1Z3Mu
b3BlcmEuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu/70AdAD
I5gS8tTq95WMeVgAEUaZ1OJf3Akv1srLrcFAtBeB3rNobUkgoGH1bdgqMG7brCvW
K+QT78LCgrjogZtXD4XKE/fNNSqe6VyUvJDrusD68UfHaNFVB97j9j+kzV6RN+G0
6lKVN8Dc7cBk/relhzhJ2B9snRfS+8Bh1k9FvRLlSMVCKsXv7wqUG+vwhKl1QnPu
pfCVSAENGadjsaxQqOz9QQzoWgYQrnP3kFgFf5iKazoOln1R7hAW+WGzLOoXVb6n
5rsvor9Oxz8D8YXag0cDmOezaWaQtl7Rr0PBnaWIwALDUNlk9E7Gy0JV5XhR0v0y
K0RGlLsVsBzQJwIDAQABo4IDhzCCA4MwHwYDVR0jBBgwFoAUQ0lH589A0ZqokvKM
isqYk8/JCA8wHQYDVR0OBBYEFG6HogOgbgTfWXI0O/NTTZbhDiL1MEkGA1UdEQRC
MECCDmJ1Z3Mub3BlcmEuY29tghZidWdmaWxlcy5vcGVyYXNvZnQuY29tghZidHNm
aWxlcy5vcGVyYXNvZnQuY29tMHoGCCsGAQUFBwEBBG4wbDAkBggrBgEFBQcwAYYY
aHR0cDovL29jc3AuZGlnaWNlcnQuY29tMEQGCCsGAQUFBzAChjhodHRwOi8vd3d3
LmRpZ2ljZXJ0LmNvbS9DQUNlcnRzL0RpZ2lDZXJ0R2xvYmFsQ0EyMDQ4LmNydDAO
BgNVHQ8BAf8EBAMCBaAwDAYDVR0TAQH/BAIwADBzBgNVHR8EbDBqMDOgMaAvhi1o
dHRwOi8vY3JsMy5kaWdpY2VydC5jb20vR2xvYmFsMjA0OC0yMDA4YS5jcmwwM6Ax
oC+GLWh0dHA6Ly9jcmw0LmRpZ2ljZXJ0LmNvbS9HbG9iYWwyMDQ4LTIwMDhhLmNy
bDCCAcYGA1UdIASCAb0wggG5MIIBtQYLYIZIAYb9bAEDAAEwggGkMDoGCCsGAQUF
BwIBFi5odHRwOi8vd3d3LmRpZ2ljZXJ0LmNvbS9zc2wtY3BzLXJlcG9zaXRvcnku
aHRtMIIBZAYIKwYBBQUHAgIwggFWHoIBUgBBAG4AeQAgAHUAcwBlACAAbwBmACAA
dABoAGkAcwAgAEMAZQByAHQAaQBmAGkAYwBhAHQAZQAgAGMAbwBuAHMAdABpAHQA
dQB0AGUAcwAgAGEAYwBjAGUAcAB0AGEAbgBjAGUAIABvAGYAIAB0AGgAZQAgAEQA
aQBnAGkAQwBlAHIAdAAgAEMAUAAvAEMAUABTACAAYQBuAGQAIAB0AGgAZQAgAFIA
ZQBsAHkAaQBuAGcAIABQAGEAcgB0AHkAIABBAGcAcgBlAGUAbQBlAG4AdAAgAHcA
aABpAGMAaAAgAGwAaQBtAGkAdAAgAGwAaQBhAGIAaQBsAGkAdAB5ACAAYQBuAGQA
IABhAHIAZQAgAGkAbgBjAG8AcgBwAG8AcgBhAHQAZQBkACAAaABlAHIAZQBpAG4A
IABiAHkAIAByAGUAZgBlAHIAZQBuAGMAZQAuMB0GA1UdJQQWMBQGCCsGAQUFBwMB
BggrBgEFBQcDAjANBgkqhkiG9w0BAQUFAAOCAQEAoSsi7eCjM1yQjiTCL5+WT1+n
Hs5sCw4Zu+bOqar1arLqkdJgTUluQphVYlKGQMebnkJ/rZyGjoQmEHKK5M9VP4xG
iDuxlYzIE55QleGAD08zJrwlrpgzkKgdlKKzIQ9ldGD8vBrPEs+8elcaCGEvbK3L
KRPgnhYpOb9icPKBk0FhMSyqQSK9Mz54IPkPuD/7tm/hN/VW8nF/ibCi33dK2y0Q
j7vcwo8GoAi9dl414C+wsGiduHpT66rhbbrnTW48aHy1o3Ik8/gIZ4/h3G8zQFJG
hWnfI7Yg8bxdS4436x6yHgSCoPNlqcQNDQdSuWgbv8mRem1rdtY1zS1N6RHlxQ==
"""
										)
		
		if not test_digicert.IsSignedBy(test_entrust):
			raise

		if not test_bugs.IsSignedBy(test_digicert):
			raise
		
		hostnames = test_bugs.ExtractHostnames();
		if "SAN_DNS" not in hostnames or "Common Name" not in hostnames:
			raise

		temp = hostnames["Common Name"]
		if not (len(temp) == 1 and
				'bugs.opera.com' in temp):
			raise
			
		temp = hostnames["SAN_DNS"]
		if not (len(temp) == 3 and
				'bugs.opera.com' in temp and 
				'bugfiles.operasoft.com' in temp and
				'btsfiles.operasoft.com' in temp):
			raise
		
		if test_bugs.Keysize() != 2048:
			raise
		if test_digicert.Keysize() != 2048:
			raise
		if test_entrust.Keysize() != 2048:
			raise
		
		certs = certhandler.CertificateLoadP7("iecerts.p7b")
		
		for cert in certs:
			if not cert.IsSelfSigned():
				print cert.SubjectNameLine()
				raise
			

		print "completed"
if __name__ == "__main__":
	import sys;
	sys.argv = ['', 'Test.testName']
	unittest.main()	