import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { SupportedInputSchema } from "./schemas";

export class API {
  static API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

  static useGetSupportedInputs = () => {
    return useQuery({
      queryKey: ["supported_inputs"],
      queryFn: async () => {
        const res = await axios.get(`${API.API_URL}/supported_inputs`);

        const data = SupportedInputSchema.safeParse(res.data);

        if (!data.success) {
          console.error("Invalid response for supported inputs:", data.error);
          throw new Error("Invalid response for supported inputs");
        }

        return data.data;
      },
      staleTime: Infinity, // Infinite until we add the ability to change the model
    });
  };
}
