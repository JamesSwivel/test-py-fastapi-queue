from typing import (
    Final,
    Union,
    Callable,
    TypeVar,
    List,
    TypedDict,
    Dict,
    Any,
    NoReturn,
    Annotated,
    Optional,
    NotRequired,
    cast,
)
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel, Field, validator

import util as U
from util.fastApi import throwHttpPrefix


###########################################################################
### CompanyResponseBM and CompanyResponse
###########################################################################
###-----------------------------------------------
class AddressBM(BaseModel):
    street: str
    postalCode: Optional[str]


class Address(TypedDict):
    street: str
    postalCode: Optional[str]


###-----------------------------------------------
class PersonBM(BaseModel):
    name: str
    age: int
    address: AddressBM


class Person(TypedDict):
    name: str
    age: int
    address: Address


###-----------------------------------------------
class DepartmentBM(BaseModel):
    name: str
    region: str
    persons: List[PersonBM]


class Department(TypedDict):
    name: str
    region: str
    persons: List[Person]


###-----------------------------------------------
class CompanyBM(BaseModel):
    name: str
    extra1: Optional[str]
    extra2: Optional[str] = Field(None, description="payload extra2")
    departments: Dict[str, DepartmentBM]


class Company(TypedDict):
    name: str
    extra1: Optional[str]
    extra2: NotRequired[Optional[str]]
    departments: Dict[str, Department]


###-----------------------------------------------
class CompanyResponseBM(BaseModel):
    data: CompanyBM


class CompanyResponse(BaseModel):
    data: CompanyBM


###########################################################################


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.post("/nestedPayload", response_model=CompanyResponseBM)
    async def nestedPayload(data: CompanyBM):
        funcName = nestedPayload.__name__
        prefix = funcName
        try:
            return {"data": data}
        except Exception as e:
            throwHttpPrefix(prefix, e)

    @app.post("/validateNestedPayload")
    async def validateNestedPayload():
        funcName = validateNestedPayload.__name__
        prefix = funcName
        try:
            data: Company = {
                "name": "Swivel Software Limited",
                "extra1": None,
                "extra2": None,
                "departments": {
                    "IT": {
                        "name": "IT Department",
                        "region": "HKSTP",
                        "persons": [
                            {
                                "name": "Ken Chan",
                                "age": 30,
                                "address": {"street": "18W HKSTP Road", "postalCode": "HKG"},
                            },
                            {"name": "Sylvia Law", "age": 21, "address": {"street": "HKU road", "postalCode": None}},
                        ],
                    },
                    "HR": {"name": "HR Department", "region": "KWun Tong APM", "persons": []},
                },
            }
            company = CompanyBM(**cast(dict, data))
            return company
        except Exception as e:
            throwHttpPrefix(prefix, e)
