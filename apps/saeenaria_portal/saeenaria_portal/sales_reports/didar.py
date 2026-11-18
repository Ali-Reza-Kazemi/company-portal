"""Official read-only Didar endpoints. Never log request URLs containing API keys."""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

PATHS = {
    "segments": "/api/Segment/GetList",
    "contacts": "/api/contact/PersonSearch",
    "companies": "/api/contact/CompanySearch",
    "contact_detail": "/api/contact/GetContactDetail",
    "deals": "/api/deal/search_v2",
    "activities": "/api/activity/search",
    "pipelines": "/api/pipeline/list/0",
    "users": "/api/User/List",
    "custom_fields": "/api/customfield/GetCustomfieldList",
    "invoice": "/api/AccountingInvoice/Get",
    "deal_detail": "/api/deal/getdealdetail",
}


class DidarError(Exception):
    pass


def local_time(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise DidarError("Didar returned a timestamp without timezone")
    return parsed.astimezone(ZoneInfo("Asia/Tehran")).isoformat()


class Client:
    def __init__(self, key, session=None, progress=None):
        self.key = key
        self.session = session or requests.Session()
        self.progress = progress or (lambda message: None)

    def request(self, resource, body=None):
        if resource not in PATHS or not self.key:
            raise DidarError("Didar API key is required")
        for attempt in range(3):
            try:
                response = self.session.post(
                    "https://app.didar.me" + PATHS[resource],
                    params={"apikey": self.key},
                    json=body,
                    timeout=(10, 90),
                    allow_redirects=False,
                )
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                if response.status_code != 200:
                    raise DidarError("Didar HTTP " + str(response.status_code))
                payload = response.json()
                if not isinstance(payload, dict) or "Response" not in payload:
                    raise DidarError("Invalid Didar response")
                return payload["Response"]
            except requests.RequestException:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise DidarError("Didar connection failed") from None
            except ValueError:
                raise DidarError("Invalid Didar JSON") from None

    def pages(self, resource, body):
        output, seen = [], set()
        offset = 0
        while offset < 100000:
            self.progress(
                ({'deals': 'دریافت معاملات دیدار', 'contacts': 'دریافت گروه مشتریان دیدار'}.get(resource, 'دریافت فعالیت‌های مرتبط'))
                + "؛ "
                + str(offset)
                + " رکورد"
            )
            data = self.request(resource, {**body, "From": offset, "Limit": 500})
            # The live activity API represents an empty result as List:null, Total:0.
            total_field = "TotalCount" if resource in ("deals", "contacts") else "Total"
            if isinstance(data, dict) and data.get("List") is None and data.get(total_field) == 0:
                if offset:
                    raise DidarError("Didar results changed during pagination")
                return output
            if not isinstance(data, dict) or not isinstance(data.get("List"), list):
                raise DidarError("Invalid Didar page")
            records = data["List"]
            for row in records:
                if not row.get("Id") or row["Id"] in seen:
                    raise DidarError("Unstable Didar pagination")
                seen.add(row["Id"])
            output.extend(records)
            offset += len(records)
            total = data.get(total_field)
            if total is not None and offset >= int(total):
                return output
            if not records:
                if total is not None and offset < int(total):
                    raise DidarError("Incomplete Didar page")
                return output
        raise DidarError("Didar extraction limit exceeded")

    def load(self, start, end):
        self.progress("دریافت کاریزهای دیدار")
        pipelines = self.request("pipelines")
        if not isinstance(pipelines, list):
            raise DidarError("Invalid Didar pipelines")
        titles = {r["Id"]: r["Title"] for r in pipelines}
        # Read all deals so old deals closed this month remain in conversion counts.
        raw = self.pages("deals", {"Criteria": {"IsDeleted": False, "Sort": 0}})
        deals = [
            dict(
                source_id=r["Id"],
                title=r.get('Title') or '',
                code=r.get('Code'),
                customer_ids=next(([r[k]['Id']] for k in ('Company', 'Contact', 'Person')
                                   if isinstance(r.get(k), dict) and r[k].get('Id')
                                   and r[k]['Id'] != '00000000-0000-0000-0000-000000000000'), []),
                updated_at=r.get("LastUpdateTime"),
                pipeline=titles.get(r.get("PipelineId")),
                seller=r.get("OwnerId"),
                seller_name=(r.get("Owner") or {}).get("DisplayName"),
                customer_owners=[
                    dict(customer_id=r[k].get("Id"), name=r[k].get("DisplayName") or r[k].get("Name"), seller=r[k]["OwnerId"])
                    for k in ("Contact", "Person", "Company")
                    if isinstance(r.get(k), dict) and r[k].get("OwnerId") and r[k].get("Id")
                ],
                customer_names=list(
                    {
                        str(
                            (r.get(k) or {}).get("DisplayName")
                            or (r.get(k) or {}).get("Name")
                            or ""
                        ).strip()
                        for k in ("Contact", "Person", "Company")
                    }
                    - {""}
                ),
                state={"Won": 1, "Lost": 2, "Pending": 0}.get(r.get("Status"), 0),
                registered_at=local_time(r.get("RegisterTime")),
                won_at=local_time(r.get("ChangeToWonTime")),
                lost_at=local_time(r.get("ChangeToLossTime")),
            )
            for r in raw
        ]
        # Follow-up coverage only needs activities on deals registered in this month.
        # Query each deal explicitly: the account-wide activity search has unstable ties
        # across pages. Keep the full date range because DoneDate can differ from DueDate.
        acts = []
        for deal in deals:
            if not str(start) <= str(deal["registered_at"] or "")[:10] <= str(end):
                continue
            acts.extend(
                self.pages(
                    "activities",
                    {
                        "DealId": deal["source_id"],
                        "IsDone": True,
                        "IsDeleted": False,
                        "FromDate": "1800-01-01T00:00:00Z",
                        "ToDate": "9999-01-01T00:00:00Z",
                        "SortType": 1,
                    },
                )
            )
        activities = [
            dict(
                source_id=r.get("DealId"),
                done_at=local_time(r.get("DoneDate")),
                state=int(r.get("IsDone") is True),
            )
            for r in acts
        ]
        sellers = {}
        for deal in deals:
            if deal["seller"] and deal["seller_name"]:
                sellers[deal["seller"]] = deal["seller_name"]
        self.progress("دریافت کارشناسان فعال دیدار")
        users = self.request("users")
        if not isinstance(users, list):
            raise DidarError("Invalid Didar users")
        choices, aliases, inactive, emails = {}, {}, [], {}
        for user in users:
            name = str(
                user.get("DisplayName")
                or " ".join(str(user.get(k) or "") for k in ("FirstName", "LastName"))
            ).strip()
            identities = [
                user.get(field)
                for field in ("UserId", "Id")
                if user.get(field) and user[field] != "00000000-0000-0000-0000-000000000000"
            ]
            username = str(user.get("UserName") or "").strip().casefold()
            if identities and "@" in username:
                emails[username] = identities[0]
            if name and identities and not user.get("IsDisabled"):
                choices[identities[0]] = name
            if identities and user.get("IsDisabled"):
                inactive.extend(identities)
            for field in ("Id", "UserId"):
                identity = user.get(field)
                if name and identity and identity != "00000000-0000-0000-0000-000000000000":
                    sellers[identity] = name
                    aliases[identity] = identities[0]
        for identity, name in sellers.items():
            if identity not in aliases and identity not in inactive:
                choices[identity] = name
        for deal in deals:
            for contact in deal["customer_owners"]:
                contact["seller"] = aliases.get(contact["seller"], contact["seller"])
                contact["active"] = contact["seller"] in choices
        return (
            deals,
            activities,
            sellers,
            titles,
            {"choices": choices, "aliases": aliases, "inactive": inactive, "emails": emails},
        )

    def enrich_documents(self, deals, sales, cache_path=None):
        """Fetch only relevant document details; cache minimal fields, never contacts or keys."""
        import json
        from uuid import uuid4
        from .matching import nearby, identity_matches

        invoices = {}
        for row in sales:
            if row.get('DocumentType') != 'Sale':
                continue
            invoices[str(row['DocumentId'])] = dict(
                date=str(row['DocumentDate'])[:10],
                customer=' '.join(dict.fromkeys(str(row.get(k) or '').strip() for k in ('CustomerName', 'CustomerLastName'))).strip(),
                quotation_creator_seller=row.get('QuotationCreatorSeller'),
            )
        selected = [d for d in deals if d.get('state') != 2 and any(
            nearby(i['date'], d) and identity_matches(i, d) for i in invoices.values())]
        cache = {}
        if cache_path and cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                cache = {}
        for index, deal in enumerate(selected):
            self.progress(f'تطبیق ریز اقلام دیدار؛ {index + 1} از {len(selected)} معامله')
            entry = cache.get(deal['source_id'], {})
            if entry.get('updated_at') != deal.get('updated_at') or time.time() - entry.get('fetched_at', 0) > 21600:
                detail = self.request('deal_detail', {'Id': deal['source_id']})
                if not isinstance(detail, dict) or detail.get('Id') != deal['source_id']:
                    raise DidarError('Invalid Didar document detail')
                fields = ('ProductCode', 'Quantity', 'UnitPrice', 'Price', 'Discount', 'TaxPrice')
                entry = dict(updated_at=deal.get('updated_at'), fetched_at=time.time(),
                             items=[{k:r.get(k) for k in fields} for r in detail.get('Items') or []],
                             document_total=detail.get('FinalAdjustmentPrice'))
                cache[deal['source_id']] = entry
            deal.update(items=entry.get('items', []), document_total=entry.get('document_total'))
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp = cache_path.with_name(uuid4().hex + '.tmp')
            temp.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
            temp.replace(cache_path)
        return len(selected)

    def enrich_customer_channels(self, deals):
        from .matching import customer_name
        self.progress('دریافت گروه‌بندی مشتریان دیدار')
        segments = self.request('segments', {})
        if not isinstance(segments, list):
            raise DidarError('Invalid Didar segments')
        def flatten(nodes):
            for node in nodes:
                yield node
                yield from flatten(node.get('Segments') or [])
        target = 'همکار/ابزار فروش'
        tag_ids = {r['Id'] for r in flatten(segments)
                   if customer_name(r.get('Title')).replace(' ', '') == target.replace(' ', '')}
        if not tag_ids:
            raise DidarError('Reseller customer segment not found')
        # Contact sorting has ties across pages in this account. Read one bounded
        # result and verify completeness rather than accepting duplicates or omissions.
        indexed = {}
        for resource in ('contacts', 'companies'):
            self.progress('دریافت گروه اشخاص و شرکت‌های دیدار')
            data = self.request(resource, {'Criteria': {'IsDeleted': 0, 'SortOrder': 1}, 'From': 0, 'Limit': 10000})
            contacts = data.get('List') if isinstance(data, dict) else None
            if not isinstance(contacts, list) or len(contacts) != data.get('TotalCount') or len({r.get('Id') for r in contacts}) != len(contacts):
                raise DidarError('Incomplete Didar customer directory')
            indexed.update({r['Id']:r for r in contacts})
        catalog = []
        for identity, record in indexed.items():
            if record.get('IsDeleted'):
                continue
            labels = record.get('Segments') or []
            ids = {s.get('Id') if isinstance(s, dict) else s for s in labels}
            catalog.append(dict(id=identity, name=record.get('DisplayName') or '', reseller=bool(ids & tag_ids)))
        tagged = {r['id'] for r in catalog if r['reseller']}
        for deal in deals:
            deal['customer_reseller'] = bool(set(deal.get('customer_ids', [])) & tagged)
        return catalog
