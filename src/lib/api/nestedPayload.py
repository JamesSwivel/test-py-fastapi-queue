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
)
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel, Field, validator

import util as U
from util.fastApi import throwHttpPrefix


class Address(BaseModel):
    street: str
    postalCode: Optional[str]


class Person(BaseModel):
    name: str
    age: int
    address: Address


class Department(BaseModel):
    name: str
    region: str
    persons: List[Person]


class Company(BaseModel):
    name: str
    extra1: Optional[str]
    extra2: Optional[str] = Field(None, description="payload extra2")
    departments: Dict[str, Department]


class CompanyResponse(BaseModel):
    data: Company


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.post("/nestedPayload", response_model=CompanyResponse)
    async def nestedPayload(data: Company):
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
            data = {
                "name": "Swivel Software Limited",
                "extra1": None,
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
                    "HR": {"name": "HR Department", "region": "KWun Tong APM", "persons": [1]},
                },
            }
            company = Company(**data)
            return company
        except Exception as e:
            throwHttpPrefix(prefix, e)
