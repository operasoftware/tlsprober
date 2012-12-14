/* -*- Mode: c++; tab-width: 4; indent-tabs-mode: t; c-basic-offset: 4 -*-
**
**   Copyright 2010-2012 Opera Software ASA
**
**   Licensed under the Apache License, Version 2.0 (the "License");
**  you may not use this file except in compliance with the License.
**  You may obtain a copy of the License at
**
**       http://www.apache.org/licenses/LICENSE-2.0
**
**   Unless required by applicable law or agreed to in writing, software
**   distributed under the License is distributed on an "AS IS" BASIS,
**   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
**   See the License for the specific language governing permissions and
**   limitations under the License.
*/

/* This file is a Python extension */

/*
 * This module retrieves information from a certificate using OpenSSL,
 * and returns the content in Python objects.
 *
 * The module is compiled using build_certhandler.py
 */

#include <Python.h>
#include <datetime.h>
#include <stdio.h>
#include <ctype.h>

#include "openssl/evp.h"
#include "openssl/err.h"
#include "openssl/x509.h"
#include "openssl/x509v3.h"

typedef bool BOOL;
#define TRUE true
#define FALSE false

typedef unsigned char byte;
typedef void *(*d2i_fun)(void *, const unsigned char **in, long len);
typedef int (*i2d_fun)(void *obj, unsigned char **out);

#define CLASSFUNC_DECL_NOARG(cl, fun) \
PyObject *cl##_##fun(cl *self)		\
{									\
	return self->fun();				\
}									\
									\
PyObject *cl ::fun()

#define CLASSFUNC_REF_NOARG(apiname, cl, fun, doc) \
	{apiname , (PyCFunction) cl##_##fun , METH_NOARGS, doc}

#define CLASSFUNC_DECL_ARG(cl, fun, argname) \
PyObject *cl##_##fun(cl *self, PyObject *argname)\
{									\
	return self->fun(argname);				\
}									\
									\
PyObject *cl :: fun(PyObject *argname)

#define CLASSFUNC_REF_ARG(apiname, cl, fun, argmode, doc) \
	{apiname , (PyCFunction) cl##_##fun , argmode, doc}

class CertStatus
{
public:
	X509_STORE *g_store;

public:
	~CertStatus()
	{
		X509_STORE_free(g_store);
	}
};

static CertStatus g_status = {NULL};
static char temp_buffer[2048];
static int cert_count = 0;
static int cert_count_active = 0;

byte *Base64toDER(const char *str, size_t &der_len)
{
	der_len = 0;
	if(str == NULL || !*str)
	{
		return NULL;
	}
	size_t str_len = strlen(str);

	size_t est_len = ((str_len +3)/4)*3;

	byte *buf = (byte *) OPENSSL_malloc(est_len);

	if(buf == NULL)
	{
		return NULL; // OOM
	}

	EVP_ENCODE_CTX base_64;
	EVP_DecodeInit(&base_64);

	int target_len = 0;
	int t_len1 = 0;

	EVP_DecodeUpdate(&base_64, buf, &target_len, (const unsigned char *) str, (int)str_len);
	EVP_DecodeFinal(&base_64, buf+target_len, &t_len1);
	target_len += t_len1;

	assert(target_len < est_len);

	der_len = target_len;

	return buf;
}

char *DERtoBase64(const byte *der_buf, size_t der_len)
{
	if(der_buf == NULL || der_len == 0)
		return NULL;

	size_t est_str_len = ((der_len +2)/3)*4;
	est_str_len += 2*est_str_len/45 +10;

	char *str_buf = (char *) OPENSSL_malloc(est_str_len);

	if(str_buf == NULL)
		return NULL; // OOM

	EVP_ENCODE_CTX base_64;
	EVP_EncodeInit(&base_64);

	int target_len = 0;
	int t_len1 = 0;

	EVP_EncodeUpdate(&base_64, (unsigned char *) str_buf, &target_len, der_buf, (int)der_len);
	EVP_EncodeFinal(&base_64, (unsigned char *) str_buf+target_len, &t_len1);
	target_len += t_len1;
	str_buf[target_len]='\0';

	assert(target_len < est_str_len);

	return str_buf;
}


void *Base64d2i(const char *cert_str, d2i_fun d2i)
{
	if(d2i==NULL)
	{
		return NULL;
	}

	size_t der_len = 0;
	byte *cer_der = Base64toDER(cert_str, der_len);

	if(cer_der == NULL)
	{
		return NULL;
	}
	if(der_len == 0)
	{
		OPENSSL_free(cer_der);
		return NULL;
	}

	const byte *cert_buf = cer_der;
	void *cert = d2i(NULL, &cert_buf, (int) der_len);

	OPENSSL_free(cer_der);
	return cert;
}

char *i2Base64(void *item, i2d_fun i2d)
{
	if(i2d ==NULL || item == NULL)
		return NULL;

	byte *der_buf = NULL;
	size_t der_len = i2d(item, &der_buf);

	if(der_buf == NULL)
		return NULL;

	char *b64_str = DERtoBase64(der_buf,der_len);

	OPENSSL_free(der_buf);

	return b64_str;
}

#define Base64ToX509(certstr) (X509 *) Base64d2i(certstr, (d2i_fun) d2i_X509)

#define X509NameToBase64(item) i2Base64(item, (i2d_fun) i2d_X509_NAME)


class Certificate
{
public:
	PyObject_HEAD;
private:
	X509 *certificate;
	BOOL invalid_name;

	PyObject *hostnames;

public:
	void Init(){certificate=NULL; invalid_name=FALSE;hostnames=NULL;}
	BOOL Construct(PyObject *args, PyObject *kwds);
	BOOL Construct(X509 *cert);
	void Destruct(){X509_free(certificate);
					certificate=NULL;
					Py_XDECREF(hostnames);
					hostnames = NULL;
					}
	PyObject *ExtractIssuerName();
	PyObject *ExtractSubjectName();
	PyObject *ExtractIssuerNameOneline();
	PyObject *ExtractSubjectNameOneline();
	PyObject *ExtractAIA_URL();
	PyObject *IsSelfSigned();
	PyObject *IsSignedBy(PyObject *args);
	PyObject *IsCertificateAuthority();
	PyObject *IsSSLServer();

	PyObject *ExtractHostnames();
	PyObject *Keysize();
	PyObject *KeyHash();
	PyObject *SigMethod();

	PyObject *GetValidFrom();
	PyObject *GetValidTo();

	PyObject *GetPolicyOIDs();

	PyObject *GetSerialNumber();

private:
	PyObject *ConvertTimeToDate(ASN1_TIME *t);
};

BOOL Certificate::Construct(PyObject *args, PyObject *kwds)
{
	certificate = NULL;
	invalid_name = FALSE;
	hostnames = NULL;

	const char *cert_str = NULL;
	if(!PyArg_ParseTuple(args, "s", &cert_str))
	{
		printf("a\n");
		return FALSE;
	}
	//printf("a1\n====\n %s\n=====\n", cert_str);

	X509 *cert = Base64ToX509(cert_str);

	if(cert == NULL)
	{
		//printf("b\n");
		return FALSE;
	}

	certificate = cert;
	return TRUE;
}

BOOL Certificate::Construct(X509 *cert)
{
	invalid_name = FALSE;
	hostnames = NULL;

	certificate = cert;
	if(certificate == NULL)
		return FALSE;

	CRYPTO_add(&certificate->references,1,CRYPTO_LOCK_X509);
	return TRUE;
}

CLASSFUNC_DECL_NOARG(Certificate,ExtractIssuerName)
{
	X509_NAME *name = X509_get_issuer_name(certificate);

	char *b64 = X509NameToBase64(name);

	PyObject *return_val = PyString_FromString(b64);

	OPENSSL_free(b64);

	return return_val;
}


static PyObject *ConvertInt(ASN1_INTEGER *value)
{

	unsigned long val = ASN1_INTEGER_get(value);

	if(val != 0xffffffff)
	{
		return PyInt_FromLong(val);
	}
	
	char *pos = (char *) temp_buffer;
	int n = sizeof(temp_buffer)-1;
	
	if(value->length *2 > n-10)
		return PyByteArray_FromStringAndSize((char *) value->data, value->length);
		
	*(pos ++) = '0';
	*(pos ++) = 'x';
	n-=2;
	
	unsigned char *p = value->data;
	int i = value->length;
	while (i>0 && n>0)
	{
		unsigned char val1= *(p++);
		i--;
		*(pos++) = "0123456789ABCDEF"[(val1>>4)&0xf];
		*(pos++) = "0123456789ABCDEF"[val1&0xf];
	}
	*pos = '\0';
	
	return PyString_FromString((char *) temp_buffer);
}


CLASSFUNC_DECL_NOARG(Certificate,GetSerialNumber)
{
	ASN1_INTEGER *sn = X509_get_serialNumber(certificate);

	return ConvertInt(sn);
}


CLASSFUNC_DECL_NOARG(Certificate,ExtractSubjectName)
{
	X509_NAME *name = X509_get_subject_name(certificate);

	char *b64 = X509NameToBase64(name);

	PyObject *return_val = PyString_FromString(b64);

	OPENSSL_free(b64);

	return return_val;
}

CLASSFUNC_DECL_NOARG(Certificate,ExtractIssuerNameOneline)
{
	X509_NAME *name = X509_get_issuer_name(certificate);

	char *liner = X509_NAME_oneline(name, NULL,0);

	PyObject *return_val = PyString_FromString(liner);

	OPENSSL_free(liner);

	return return_val;
}

CLASSFUNC_DECL_NOARG(Certificate,ExtractSubjectNameOneline)
{
	X509_NAME *name = X509_get_subject_name(certificate);

	char *liner = X509_NAME_oneline(name, NULL,0);

	PyObject *return_val = PyString_FromString(liner);

	OPENSSL_free(liner);

	return return_val;
}

CLASSFUNC_DECL_NOARG(Certificate,GetPolicyOIDs)
{
	PyObject *return_list =  PyList_New(0);
	if(!return_list)
		return NULL;

	int i=0;
	CERTIFICATEPOLICIES *policies = (CERTIFICATEPOLICIES *) X509_get_ext_d2i(certificate, NID_certificate_policies, &i, NULL);

	for (i = 0; i < sk_POLICYINFO_num(policies); i++)
	{
		POLICYINFO *policy = sk_POLICYINFO_value(policies, i);
		if(OBJ_obj2txt(temp_buffer, sizeof(temp_buffer)-1,policy->policyid,1)<=0)
		{
			printf( "a\n");
			return NULL;
		}
		temp_buffer[ sizeof(temp_buffer)-1]=0;
		PyList_Append(return_list, PyString_FromString(temp_buffer));
	}
	CERTIFICATEPOLICIES_free(policies);

	return return_list;
}

CLASSFUNC_DECL_NOARG(Certificate,IsSelfSigned)
{
	int issued = X509_check_issued(certificate,certificate);

	return PyBool_FromLong(issued == 0);
}

CLASSFUNC_DECL_ARG(Certificate,IsSignedBy, signer_cert)
{
	if(signer_cert == NULL)
		return NULL;

	if(!PyObject_IsInstance(signer_cert, (PyObject *) ob_type))
		Py_RETURN_FALSE;

	int issued = X509_check_issued(((Certificate *) signer_cert)->certificate,certificate);

	return PyBool_FromLong(issued == 0);
}

CLASSFUNC_DECL_NOARG(Certificate,IsCertificateAuthority)
{
	int is_ca = X509_check_ca(certificate);

	//printf("ca %d\n", is_ca);fflush(stdout);

	return PyBool_FromLong(is_ca != 0);
}

CLASSFUNC_DECL_NOARG(Certificate,IsSSLServer)
{
	int is_ssl = X509_check_purpose(certificate, X509_TRUST_SSL_SERVER, 0);
	int issued = X509_check_issued(certificate,certificate);

	//printf("issued %d\n", issued);fflush(stdout);
	//printf("ssl %d\n", is_ssl); fflush(stdout);
	return PyBool_FromLong(is_ssl != 0 && issued != 0);
}


CLASSFUNC_DECL_NOARG(Certificate,Keysize)
{
	EVP_PKEY *key = X509_get_pubkey(certificate);

	return PyInt_FromLong(EVP_PKEY_bits(key));
}

static const char hexbytes[]="0123456789ABCDEF";

CLASSFUNC_DECL_NOARG(Certificate,KeyHash)
{
	ASN1_BIT_STRING *key=certificate->cert_info->key->public_key;
	byte md_buf[EVP_MAX_MD_SIZE];
	char hex_buf[EVP_MAX_MD_SIZE*2+1];
	unsigned int hash_len=0;
	int i;
	char *hex_pos;
	byte *md_pos;

	EVP_Digest(key->data, key->length,md_buf,&hash_len, EVP_sha256(),NULL);
	hex_pos = hex_buf;
	md_pos = md_buf;
	for (i=hash_len;i>0;i--)
	{
		byte val = *(md_pos++);
		*(hex_pos++) = hexbytes[val&0xf];
		*(hex_pos++) = hexbytes[(val>>4)&0xf];
	}
	*hex_pos = '\0';

	return PyString_FromString(hex_buf);
}

CLASSFUNC_DECL_NOARG(Certificate,SigMethod)
{
	return PyString_FromString(OBJ_nid2sn(OBJ_obj2nid(certificate->sig_alg->algorithm)));
}

CLASSFUNC_DECL_NOARG(Certificate,ExtractHostnames)
{
	if(hostnames)
		return hostnames;
	X509_EXTENSION *ext;
	STACK_OF(X509_EXTENSION) *ext_stack;
	X509_NAME_ENTRY *ne;
	X509_NAME *certname;
	ASN1_IA5STRING *name_string;
	long field;

	PyObject *CN_items = PyList_New(0);
	PyObject *SAN_DNS_items = PyList_New(0);
	PyObject *SAN_IP_items = PyList_New(0);
	PyObject *NSSN_item = NULL;

	ext_stack = certificate->cert_info->extensions;
	BOOL OK=TRUE;

	if(CN_items == NULL || SAN_DNS_items == NULL || SAN_IP_items == NULL)
	{
		OK = FALSE;
	}

	if(OK && ext_stack != NULL){
		field = X509v3_get_ext_by_NID(ext_stack,NID_subject_alt_name,-1);

		if(field >=0)
		{
			STACK_OF(GENERAL_NAME) *names = NULL;

			ext= X509v3_get_ext(ext_stack,field);

			if(ext && (names = (STACK_OF(GENERAL_NAME) *) X509V3_EXT_d2i(ext)) != NULL)
			{
				GENERAL_NAME *name;
				int i;

				for(i = 0; OK && i< sk_GENERAL_NAME_num(names); i++)
				{
					name = sk_GENERAL_NAME_value(names, i);
					switch(name->type)
					{
					case GEN_DNS:
						{
							PyObject *str1 = PyString_FromStringAndSize((const char *) name->d.dNSName->data, name->d.dNSName->length);

							PyObject *str2 = NULL;
							if(str1)
							{
								PyObject *str2 = PyString_AsDecodedObject(str1, "windows_1252", "replace");
								Py_DECREF(str1);
							}

							if(!str2 || PyList_Append(SAN_DNS_items, str2))
							{
								OK=FALSE;
								break;
							}
						}
						break;
					case GEN_IPADD:
						{
							if(PyList_Append(SAN_IP_items, PyByteArray_FromStringAndSize((const char *) name->d.iPAddress->data, name->d.iPAddress->length)) < 0)
							{
								OK=FALSE;
								break;
							}
						}
						break;
					}
				}
			}
			sk_GENERAL_NAME_pop_free(names, GENERAL_NAME_free);
		}

		field = X509v3_get_ext_by_NID(ext_stack,NID_netscape_ssl_server_name,-1);

		if(field >=0)
		{
			ext= X509v3_get_ext(ext_stack,field);

			if(ext)
			{
				name_string = (ASN1_IA5STRING *) X509V3_EXT_d2i(ext);
				if(name_string) {
					NSSN_item = PyString_FromStringAndSize((const char *)name_string->data, name_string->length);
					if(NSSN_item == NULL)
					{
						OK = FALSE;
					}
				}
			}
		}
	}

	certname = X509_get_subject_name(certificate);
	if(OK &&certname != NULL)
	{
		field = -1;

		do{
			field = X509_NAME_get_index_by_NID(certname, NID_commonName,field);

			if(field>=0)
			{
				ne=(X509_NAME_ENTRY *)X509_NAME_get_entry(certname,field);

				if(field>=0)
				{
					if(ne->value->type == V_ASN1_BMPSTRING)
					{
						int bo=1;
						if(PyList_Append(CN_items, PyUnicode_DecodeUTF16((const char *) ne->value->data, ne->value->length, NULL, &bo))<0)
						{
							OK = FALSE;
							break;
						}
					}
					else if(PyList_Append(CN_items, PyString_FromStringAndSize((const char *) ne->value->data, ne->value->length))<0)
					{
						OK = FALSE;
						break;
					}
				}
			}
		}while(field >= 0);
	}

	PyObject *return_dict = NULL;

	if(OK)
	{
		return_dict = PyDict_New();
		if (return_dict &&(
		    ( PyList_Size(SAN_DNS_items) > 0  && PyDict_SetItemString(return_dict, "SAN_DNS", SAN_DNS_items) < 0) ||
			( PyList_Size(SAN_IP_items) > 0  && PyDict_SetItemString(return_dict, "SAN_IP", SAN_IP_items) < 0) ||
			(NSSN_item && PyDict_SetItemString(return_dict, "Netscape ServerName", NSSN_item) < 0) ||
			( PyList_Size(CN_items) > 0  && PyDict_SetItemString(return_dict, "Common Name", CN_items) < 0)))
		{
			Py_XDECREF(return_dict);
			return_dict = NULL;
		}

	}

	if(!return_dict)
		Py_RETURN_NONE;

	hostnames = return_dict;
	Py_INCREF(hostnames);

	return return_dict;
}

CLASSFUNC_DECL_NOARG(Certificate,ExtractAIA_URL)
{
	X509_EXTENSION *ext;
	STACK_OF(X509_EXTENSION) *ext_stack;
	long field;

	PyObject *aia_string = NULL;

	ext_stack = certificate->cert_info->extensions;
	BOOL OK=TRUE;

	if(OK && ext_stack != NULL){
		field = X509v3_get_ext_by_NID(ext_stack,NID_info_access,-1);

		if(field >=0)
		{
			AUTHORITY_INFO_ACCESS *infoaccess = NULL;

			ext= X509v3_get_ext(ext_stack,field);

			if(ext && (infoaccess = (AUTHORITY_INFO_ACCESS *) X509V3_EXT_d2i(ext)) != NULL)
			{
				int i;
				for(i = 0; i < sk_ACCESS_DESCRIPTION_num(infoaccess); i++)
				{
					ACCESS_DESCRIPTION *info_item = sk_ACCESS_DESCRIPTION_value(infoaccess,i);
					if(info_item &&
						OBJ_obj2nid(info_item->method) == NID_ad_ca_issuers &&
						info_item->location->type == GEN_URI &&
						info_item->location->d.ia5)
					{
						aia_string = PyString_FromStringAndSize((const char *) info_item->location->d.ia5->data, info_item->location->d.ia5->length);
						break;
					}
				}
			}
			sk_ACCESS_DESCRIPTION_pop_free(infoaccess, ACCESS_DESCRIPTION_free);
		}
	}

	if(!aia_string)
		Py_RETURN_NONE;

	return aia_string;
}


PyObject *Certificate::ConvertTimeToDate(ASN1_TIME *t)
{
	ASN1_GENERALIZEDTIME *date = ASN1_TIME_to_generalizedtime(t,NULL);

	if (date == NULL)
		return PyDateTime_FromDateAndTime(1900, 1, 1, 0, 0,0,0);

	int year=0, mon=0, day=0, hour=0,min=0;

	sscanf((const char *) date->data,"%4d%2d%2d%2d%2d", &year, &mon, &day, &hour, &min);

	ASN1_GENERALIZEDTIME_free(date);

	return PyDateTime_FromDateAndTime(year, mon, day, hour, min,0,0);
}

CLASSFUNC_DECL_NOARG(Certificate,GetValidFrom)
{
	return ConvertTimeToDate(X509_get_notBefore(certificate));
}

CLASSFUNC_DECL_NOARG(Certificate,GetValidTo)
{
	return ConvertTimeToDate(X509_get_notAfter(certificate));
}

static void
Certificate_dealloc(Certificate* self)
{
	self->Destruct();
    self->ob_type->tp_free((PyObject*)self);
}

PyObject *Certificate_New(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Certificate *self;

    self = (Certificate *)type->tp_alloc(type, 0);
	if (self != NULL) {
		if(!self->Construct(args, kwds))
		{
			Py_XDECREF(self);
			Py_RETURN_NONE;
		}
	}

    return (PyObject *)self;
}

PyObject *Certificate_New(PyTypeObject *type, X509 *cert)
{
    Certificate *self;

    self = (Certificate *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->Construct(cert);
	}

    return (PyObject *)self;
}


int Certificate_init(Certificate* self, PyObject *args, PyObject *kwds)
{
	return (self->Construct(args, kwds) ? 0 : -1);
}

static PyMethodDef Certificate_methods[] = {
	CLASSFUNC_REF_NOARG("IssuerNameDER", Certificate, ExtractIssuerName, "Return the Issuername in DER Base64"),
	CLASSFUNC_REF_NOARG("SubjectNameDER", Certificate, ExtractSubjectName, "Return the Subjectname in DER Base64"),
	CLASSFUNC_REF_NOARG("IssuerNameLine", Certificate, ExtractIssuerNameOneline, "Return the Issuername in a single line form"),
	CLASSFUNC_REF_NOARG("SubjectNameLine", Certificate, ExtractSubjectNameOneline, "Return the Subjectname in a single line form"),
	CLASSFUNC_REF_NOARG("ExtractAIA_URL", Certificate, ExtractAIA_URL, "Return the AIA issuer URL"),
	CLASSFUNC_REF_NOARG("IsSelfSigned", Certificate, IsSelfSigned, "Is this a selfsigned certificate"),
	CLASSFUNC_REF_ARG("IsSignedBy", Certificate, IsSignedBy, METH_O,  "Is this certificate signed by the argument certificate"),
	CLASSFUNC_REF_NOARG("IsCertificateAuthority", Certificate, IsCertificateAuthority, "Is this a CA certificate"),
	CLASSFUNC_REF_NOARG("IsSSLServer", Certificate, IsSSLServer, "Is this a SSL Server certificate"),
    CLASSFUNC_REF_NOARG("ExtractHostnames", Certificate, ExtractHostnames,  "Extract the SSL hostname fields"),
    CLASSFUNC_REF_NOARG("Keysize", Certificate, Keysize,  "Extract the number of bits in the key"),
    CLASSFUNC_REF_NOARG("KeyHash", Certificate, KeyHash,  "Extract the hash of the key"),
    CLASSFUNC_REF_NOARG("SignatureMethod", Certificate, SigMethod,  "Extract the certificate's signature method"),
    CLASSFUNC_REF_NOARG("GetValidFrom", Certificate, GetValidFrom,  "Get The valid from date of the certificate"),
    CLASSFUNC_REF_NOARG("GetValidTo", Certificate, GetValidTo,  "Get The valid to date of the certificate"),
    CLASSFUNC_REF_NOARG("GetPolicyOIDs", Certificate, GetPolicyOIDs,  "Get The policy OIDs of the certificate"),
    CLASSFUNC_REF_NOARG("GetSerialNumber", Certificate, GetSerialNumber,  "Get The Serial Number of the certificate"),
    {NULL}  /* Sentinel */
};

static PyTypeObject cert_CertificateType = {
	PyObject_HEAD_INIT(NULL)
	0,							/*ob_size*/
	"Certificate",				/*tp_name*/
	sizeof(Certificate),		/*tp_basicsize*/
	0,							/*tp_itemsize*/
	(destructor) Certificate_dealloc,		/*tp_dealloc*/
	0,							/*tp_print*/
	0,							/*tp_getattr*/
	0,							/*tp_setattr*/
	0,							/*tp_compare*/
	0,							/*tp_repr*/
	0,							/*tp_as_number*/
	0,							/*tp_as_sequence*/
	0,							/*tp_as_mapping*/
	0,							/*tp_hash */
	0,							/*tp_call*/
	0,							/*tp_str*/
	0,							/*tp_getattro*/
	0,							/*tp_setattro*/
	0,							/*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,			/*tp_flags*/
	"OpenSSL Certificate handler",	/* tp_doc */
	0,							/* tp_traverse */
	0,							/* tp_clear */
	0,							/* tp_richcompare */
	0,							/* tp_weaklistoffset */
	0,							/* tp_iter */
	0,							/* tp_iternext */
	Certificate_methods,		/* tp_methods */
	0,							/* tp_members */
	0,							/* tp_getset */
	0,							/* tp_base */
	0,							/* tp_dict */
	0,							/* tp_descr_get */
	0,							/* tp_descr_set */
	0,							/* tp_dictoffset */
	0, //(initproc)Certificate_init,	/* tp_init */
	0,							/* tp_alloc */
	Certificate_New,			/* tp_new */
};


PyObject *CertificateLoadP7(PyObject *self, PyObject *name)
{
	if(name == NULL || PyString_AsString(name) == NULL || *PyString_AsString(name) == '\0')
		return NULL;

	BIO *p7_in = BIO_new_file(PyString_AsString(name),"r");
	if(!p7_in)
		return NULL;

	PKCS7 *p7 = d2i_PKCS7_bio(p7_in,NULL);
	if(!p7)
		return NULL;


	STACK_OF(X509) *certs = p7->d.sign->cert;

	int cert_count = sk_X509_num(certs);
	PyObject *list = PyList_New(0);

	for(int i = 0; i<cert_count; i++)
	{
		PyObject *cert = Certificate_New(&cert_CertificateType, sk_X509_value(certs, i));
		if(PyList_Append(list, (PyObject *) cert)<0)
		{
			Py_XDECREF(cert);
			Py_XDECREF(list);
			return NULL;
		}
		Py_XDECREF(cert);
	}
	return list;
}

/** Python method definition */
static PyMethodDef  certhandlerfuncs[] = {
	{"CertificateLoadP7", (PyCFunction) CertificateLoadP7, METH_O, "Load a PKCS7 encoded set of certificates"},
	{NULL, NULL, 0, NULL} /* End of list */
};

const X509_LOOKUP_METHOD x509_options_lookup =
{
	NULL, // "Load certificates from SSL options"
	NULL,			/* new */
	NULL,			/* free */
	NULL,			/* init */
	NULL,			/* shutdown */
	NULL,			/* ctrl */
	NULL, //SSL_get_cert_by_subject,/* get_by_subject */
	NULL,			/* get_by_issuer_serial */
	NULL,			/* get_by_fingerprint */
	NULL			/* get_by_alias */
};


/** Python initiator */
extern "C" PyMODINIT_FUNC
initcerthandler(void)
{
	PyDateTime_IMPORT;

	OpenSSL_add_all_algorithms();
	if(ERR_get_error())
	{
		printf("setup failed 1");
		return;
	}

	g_status.g_store = X509_STORE_new();
	if(g_status.g_store == NULL)
	{
		printf("setup failed 2");
		return;
	}
	X509_STORE_add_lookup(g_status.g_store, (X509_LOOKUP_METHOD*)&x509_options_lookup);
	//X509_STORE_set_verify_cb_func(g_status.g_store, CertificateHandler_Verify_callback);

	PyObject* m;

	if (PyType_Ready(&cert_CertificateType) < 0)
	{
		printf("setup failed 3");
		return;
	}

	m = Py_InitModule3("certhandler", certhandlerfuncs,
						"Certificate handler");

	if (m == NULL)
	{
		printf("setup failed 4");
		return;
	}

	Py_INCREF(&cert_CertificateType);
	PyModule_AddObject(m, "Certificate", (PyObject *)&cert_CertificateType);
}
