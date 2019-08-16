import routes.rest.sche

def route(api):
    api.add_resource(routes.rest.sche.Scheduler, '/api/v1/sche')
    