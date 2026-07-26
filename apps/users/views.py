from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from apps.users.services.dashboard_service import DashboardService
from utils.custom_exception import ExceptionHandler

class DashboardView(TemplateView):
    template_name = 'users/dashboard.html'

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            try:
                basin_id            = request.GET.get('basin_id')
                start_date          = request.GET.get('start_date')
                end_date            = request.GET.get('end_date')
                min_dry_gap_hours   = request.GET.get('min_dry_gap_hours', 6)

                
                # start_date          = None
                # end_date            = None
                # min_dry_gap_hours   = None
                
                if basin_id:
                    basin_id = int(basin_id)
                if min_dry_gap_hours:
                    min_dry_gap_hours = int(min_dry_gap_hours)

                data = DashboardService.get_dashboard_data(
                    basin_id=basin_id,
                    start_date=start_date,
                    end_date=end_date,
                    min_dry_gap_hours=min_dry_gap_hours
                )
                return JsonResponse({"status": "success", "data": data})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=400)

        context           = self.get_context_data(**kwargs)
        context['basins'] = DashboardService.get_basins()

        print("DashboardView context:", context)  # Debugging line
        return self.render_to_response(context)
